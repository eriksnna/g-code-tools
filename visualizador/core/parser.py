"""Interpretação de G-code. Não depende de Qt nem de numpy."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from config import ARC_STEP_DEG, DEFAULT_FEED, INCH_TO_MM, MACHINE_LIMITS

Point = tuple[float, float, float]
Limits = dict[str, tuple[float, float]]

G_RAPID = 0
G_LINEAR = 1
G_CW_ARC = 2
G_CCW_ARC = 3
G_UNITS = {20: INCH_TO_MM, 21: 1.0}
G_ABSOLUTE = 90
G_INCREMENTAL = 91
MOTION_ARCS = (G_CW_ARC, G_CCW_ARC)
AXES = "XYZ"

ERROR = "erro"
WARNING = "aviso"
BOUNDS_TOLERANCE = 1e-6

WORD_RE = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")
PAREN_COMMENT_RE = re.compile(r"\(.*?\)")
TWO_PI = 2 * math.pi


class GCodeError(ValueError):
    """Linha de G-code que não pode ser interpretada."""


@dataclass(frozen=True)
class Move:
    """Um trecho de movimento linear. Arcos viram vários Move."""
    start: Point
    end: Point
    is_cut: bool
    feed: float   # mm/min programado; relevante apenas para cortes
    line: int = 0 # linha de origem no arquivo, começando em 1

    @property
    def length(self) -> float:
        return math.dist(self.start, self.end)


@dataclass(frozen=True)
class Issue:
    """Problema encontrado no arquivo, associado a uma linha."""
    line: int
    severity: str  # ERROR ou WARNING
    message: str


@dataclass(frozen=True)
class ParseResult:
    moves: list[Move] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    commands: dict[str, int] = field(default_factory=dict)


def clean_line(raw: str) -> str:
    """Remove comentários, espaços das pontas e padroniza em maiúsculas."""
    without_parens = PAREN_COMMENT_RE.sub("", raw)
    without_semicolon = without_parens.split(";", 1)[0]
    return without_semicolon.strip().upper()


def parse_words(line: str) -> list[tuple[str, float]]:
    """'G20 G1 X10 Y-2.5' -> [('G', 20.0), ('G', 1.0), ('X', 10.0), ('Y', -2.5)]"""
    return [(letter, float(value)) for letter, value in WORD_RE.findall(line)]


def parse_gcode(text: str, default_feed: float = DEFAULT_FEED,
                limits: Limits = MACHINE_LIMITS) -> ParseResult:
    """Lê o texto inteiro e devolve os movimentos e os problemas encontrados."""
    interpreter = GCodeInterpreter(default_feed, limits)
    for lineno, raw in enumerate(text.splitlines(), start=1):
        interpreter.run_line(clean_line(raw), lineno)
    return ParseResult(
        moves=interpreter.moves,
        issues=interpreter.issues,
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
    """Mantém o estado modal da máquina enquanto percorre as linhas."""

    def __init__(self, default_feed: float, limits: Limits = MACHINE_LIMITS) -> None:
        self.position: Point = (0.0, 0.0, 0.0)
        self.absolute = True
        self.unit_scale = 1.0
        self.motion = G_RAPID
        self.feed = default_feed
        self.limits = limits
        self.moves: list[Move] = []
        self.issues: list[Issue] = []
        self.commands = {"G0": 0, "G1": 0, "G2": 0, "G3": 0}

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

        # Todos os G da linha são aplicados primeiro, na ordem em que aparecem
        for letter, value in words:
            if letter == "G":
                self._apply_g_code(int(value))

        axis_words = {letter: value for letter, value in words if letter != "G"}
        if "F" in axis_words:
            self.feed = axis_words["F"] * self.unit_scale
            self._feed_programmed = True

        if any(axis in axis_words for axis in AXES):
            self._move(axis_words)

    def _apply_g_code(self, code: int) -> None:
        if code in (G_RAPID, G_LINEAR, *MOTION_ARCS):
            self.motion = code
        elif code in G_UNITS:
            self.unit_scale = G_UNITS[code]
        elif code == G_ABSOLUTE:
            self.absolute = True
        elif code == G_INCREMENTAL:
            self.absolute = False
        # demais códigos G ainda não são interpretados

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

    # --- movimentos ---

    def _line(self, end: Point) -> None:
        if end == self.position:
            return
        is_cut = self.motion != G_RAPID
        if is_cut:
            self._check_feed()
        self._check_bounds([end])
        self.moves.append(Move(self.position, end, is_cut, self.feed, self._lineno))

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
            self.moves.append(Move(previous, point, True, self.feed, self._lineno))
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