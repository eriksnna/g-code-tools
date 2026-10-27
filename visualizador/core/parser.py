"""Interpretação de movimentos G-code. Não depende de Qt nem de numpy.

Sub-rotinas e variáveis já foram expandidas por core.expander. Os códigos de
processo (M-codes) são traduzidos pelo dialeto escolhido, não fixados aqui.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from config import ARC_STEP_DEG, DEFAULT_DIALECT, DEFAULT_FEED, INCH_TO_MM
from core.machine_profile import DEFAULT_LIMITS as MACHINE_LIMITS
from core.dialect import Dialect, get_dialect
from core.expander import expand_program
# re-exportados: quem importa de core.parser continua funcionando
from core.lexer import ERROR, WARNING, GCodeError, Issue, clean_line, parse_words

Point = tuple[float, float, float]
Limits = dict[str, tuple[float, float]]

G_RAPID = 0
G_LINEAR = 1
G_CW_ARC = 2
G_CCW_ARC = 3
G_DWELL = 4
G_UNITS = {20: INCH_TO_MM, 21: 1.0}
G_ABSOLUTE = 90
G_INCREMENTAL = 91
MOTION_ARCS = (G_CW_ARC, G_CCW_ARC)
AXES = "XYZ"
BOUNDS_TOLERANCE = 1e-6
TWO_PI = 2 * math.pi

__all__ = [
    "ERROR", "WARNING", "Issue", "Move", "ParseResult", "arc_points",
    "clean_line", "parse_gcode", "parse_words",
]


@dataclass(frozen=True)
class Move:
    """Um trecho de movimento. Arcos viram vários Move; G04 vira um Move de espera."""
    start: Point
    end: Point
    is_cut: bool
    feed: float        # mm/min programado; relevante apenas para cortes
    line: int = 0      # linha de origem no arquivo, começando em 1
    active: bool = False  # processo ligado (spindle, arco, tocha) durante o movimento
    dwell: float = 0.0    # segundos de espera (G04); quando > 0, start == end
    rapid: bool = False   # G0: deslocamento rápido, na velocidade de avanço rápido

    @property
    def length(self) -> float:
        return math.dist(self.start, self.end)


@dataclass(frozen=True)
class ParseResult:
    moves: list[Move] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    commands: dict[str, int] = field(default_factory=dict)  # G0 a G4 executados


def parse_gcode(text: str, default_feed: float = DEFAULT_FEED,
                limits: Limits = MACHINE_LIMITS,
                dialect: Dialect | None = None) -> ParseResult:
    """Expande o programa e interpreta a sequência resultante."""
    dialect = dialect or get_dialect(DEFAULT_DIALECT)
    expansion = expand_program(text)

    interpreter = GCodeInterpreter(default_feed, limits, dialect)
    for source in expansion.lines:
        interpreter.run_line(source.text, source.line)

    issues = sorted([*expansion.issues, *interpreter.issues], key=lambda issue: issue.line)
    return ParseResult(
        moves=interpreter.moves,
        issues=issues,
        commands=interpreter.commands,
    )


def arc_points(start: Point, end: Point, center: tuple[float, float],
               clockwise: bool, step_deg: float = ARC_STEP_DEG) -> list[Point]:
    """Pontos intermediários de um arco no plano XY. Z varia linearmente (hélice)."""
    cx, cy = center
    radius = math.hypot(start[0] - cx, start[1] - cy)
    a_start = math.atan2(start[1] - cy, start[0] - cx)
    a_end = math.atan2(end[1] - cy, end[0] - cx)
    sweep = _signed_sweep(a_end - a_start, clockwise)

    steps = max(1, math.ceil(abs(sweep) / math.radians(step_deg)))
    points: list[Point] = []
    for i in range(1, steps + 1):
        t = i / steps
        angle = a_start + sweep * t
        z = start[2] + (end[2] - start[2]) * t
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle), z))

    points[-1] = end  # o último ponto é exatamente o destino
    return points


def _signed_sweep(delta: float, clockwise: bool) -> float:
    """Ajusta o ângulo varrido para o sentido pedido pelo G2 ou G3."""
    if clockwise and delta >= 0:
        return delta - TWO_PI
    if not clockwise and delta <= 0:
        return delta + TWO_PI
    return delta


class GCodeInterpreter:
    """Mantém o estado modal da máquina enquanto percorre as linhas expandidas."""

    def __init__(self, default_feed: float, limits: Limits = MACHINE_LIMITS,
                 dialect: Dialect | None = None) -> None:
        self.position: Point = (0.0, 0.0, 0.0)
        self.absolute = True
        self.unit_scale = 1.0
        self.motion = G_RAPID
        self.feed = default_feed
        self.limits = limits
        self.dialect = dialect or get_dialect(DEFAULT_DIALECT)
        self.process_active = False
        self.moves: list[Move] = []
        self.issues: list[Issue] = []
        self.commands = {"G0": 0, "G1": 0, "G2": 0, "G3": 0, "G4": 0}

        self._lineno = 0
        self._feed_programmed = False
        self._feed_warned = False
        self._bounds_reported_line = 0

    def run_line(self, line: str, lineno: int) -> None:
        self._lineno = lineno
        try:
            self._execute(line)
        except GCodeError as err:
            self._report(ERROR, str(err))

    # --- interpretação da linha ---

    def _execute(self, line: str) -> None:
        words = parse_words(line)
        if not words:
            return

        g_codes = [int(value) for letter, value in words if letter == "G"]
        m_codes = [int(value) for letter, value in words if letter == "M"]
        params = {letter: value for letter, value in words if letter not in "GM"}

        # G e M são aplicados primeiro, na ordem em que aparecem na linha
        for code in g_codes:
            self._apply_g_code(code)
        for code in m_codes:
            self._apply_m_code(code)

        if "F" in params:
            self.feed = params["F"] * self.unit_scale
            self._feed_programmed = True

        if G_DWELL in g_codes:
            self._dwell(params.get("P", 0.0))

        if any(axis in params for axis in AXES):
            self._move(params)

    def _apply_g_code(self, code: int) -> None:
        if code in (G_RAPID, G_LINEAR, *MOTION_ARCS):
            self.motion = code
        elif code in G_UNITS:
            self.unit_scale = G_UNITS[code]
        elif code == G_ABSOLUTE:
            self.absolute = True
        elif code == G_INCREMENTAL:
            self.absolute = False
        # G04 é tratado em _execute, pois depende do parâmetro P

    def _apply_m_code(self, code: int) -> None:
        """M-codes de processo são definidos pelo dialeto; os demais são ignorados."""
        if code in self.dialect.process_on:
            self.process_active = True
        elif code in self.dialect.process_off:
            self.process_active = False

    def _move(self, words: dict[str, float]) -> None:
        self.commands[f"G{self.motion}"] += 1
        end = self._target(words)
        if self.motion in MOTION_ARCS:
            self._arc(end, words)
        else:
            self._line(end)
        self.position = end

    def _target(self, words: dict[str, float]) -> Point:
        def resolve(axis: str, current: float) -> float:
            if axis not in words:
                return current
            value = words[axis] * self.unit_scale
            return value if self.absolute else current + value

        x, y, z = self.position
        return (resolve("X", x), resolve("Y", y), resolve("Z", z))

    # --- movimentos e esperas ---

    def _dwell(self, duration: float) -> None:
        """G04: espera no mesmo ponto. A unidade do P vem do dialeto."""
        seconds = duration * self.dialect.dwell_unit
        if seconds <= 0:
            return
        self.commands["G4"] += 1
        self.moves.append(Move(
            start=self.position,
            end=self.position,
            is_cut=False,
            feed=self.feed,
            line=self._lineno,
            active=self.process_active,
            dwell=seconds,
        ))

    def _line(self, end: Point) -> None:
        if end == self.position:
            return
        is_cut = self.motion != G_RAPID
        if is_cut:
            self._check_feed()
        self._check_bounds([end])
        self.moves.append(Move(
            self.position, end, is_cut, self.feed, self._lineno,
            active=self.process_active,
            rapid=self.motion == G_RAPID,
        ))

    def _arc(self, end: Point, words: dict[str, float]) -> None:
        if "R" in words:
            raise GCodeError("arco com R não suportado; use I/J")

        self._check_feed()
        start = self.position
        center = (
            start[0] + words.get("I", 0.0) * self.unit_scale,
            start[1] + words.get("J", 0.0) * self.unit_scale,
        )
        points = arc_points(start, end, center, clockwise=self.motion == G_CW_ARC)
        self._check_bounds(points)

        previous = start
        for point in points:
            self.moves.append(Move(
                previous, point, True, self.feed, self._lineno,
                active=self.process_active,
            ))
            previous = point

    # --- validação ---

    def _check_feed(self) -> None:
        """Avisa uma única vez se o corte começa sem F programado."""
        if self._feed_programmed or self._feed_warned:
            return
        self._feed_warned = True
        self._report(WARNING, f"avanço F ausente; usando {self.feed:g} mm/min")

    def _check_bounds(self, points: list[Point]) -> None:
        """Reporta no máximo um problema de área de trabalho por linha."""
        if self._bounds_reported_line == self._lineno:
            return
        for point in points:
            for axis, value in zip(AXES, point):
                low, high = self.limits[axis]
                if not low - BOUNDS_TOLERANCE <= value <= high + BOUNDS_TOLERANCE:
                    self._bounds_reported_line = self._lineno
                    self._report(
                        ERROR,
                        f"fora da área de trabalho: {axis} = {value:.2f} "
                        f"(faixa {low:g} a {high:g} mm)",
                    )
                    return

    def _report(self, severity: str, message: str) -> None:
        self.issues.append(Issue(self._lineno, severity, message))