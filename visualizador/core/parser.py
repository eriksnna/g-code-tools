"""Interpretação de G-code. Não depende de Qt nem de numpy."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from config import ARC_STEP_DEG, DEFAULT_FEED, INCH_TO_MM

Point = tuple[float, float, float]

G_RAPID = 0
G_LINEAR = 1
G_CW_ARC = 2
G_CCW_ARC = 3
G_UNITS = {20: INCH_TO_MM, 21: 1.0}
G_ABSOLUTE = 90
G_INCREMENTAL = 91
MOTION_ARCS = (G_CW_ARC, G_CCW_ARC)
AXES = "XYZ"

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
    feed: float  # mm/min programado; relevante apenas para cortes

    @property
    def length(self) -> float:
        return math.dist(self.start, self.end)


@dataclass(frozen=True)
class ParseResult:
    moves: list[Move] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def clean_line(raw: str) -> str:
    """Remove comentários, espaços das pontas e padroniza em maiúsculas."""
    without_parens = PAREN_COMMENT_RE.sub("", raw)
    without_semicolon = without_parens.split(";", 1)[0]
    return without_semicolon.strip().upper()


def parse_words(line: str) -> dict[str, float]:
    """'G1 X10 Y-2.5' -> {'G': 1.0, 'X': 10.0, 'Y': -2.5}"""
    return {letter: float(value) for letter, value in WORD_RE.findall(line)}


def parse_gcode(text: str, default_feed: float = DEFAULT_FEED) -> ParseResult:
    """Lê o texto inteiro e devolve os movimentos e os avisos encontrados."""
    interpreter = GCodeInterpreter(default_feed)
    warnings: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        try:
            interpreter.run_line(clean_line(raw))
        except GCodeError as err:
            warnings.append(f"Linha {lineno}: {err}")
    return ParseResult(moves=interpreter.moves, warnings=warnings)


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

    points[-1] = end  # garante que o último ponto é exatamente o destino
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

    def __init__(self, default_feed: float) -> None:
        self.position: Point = (0.0, 0.0, 0.0)
        self.absolute = True
        self.unit_scale = 1.0
        self.motion = G_RAPID
        self.feed = default_feed
        self.moves: list[Move] = []

    def run_line(self, line: str) -> None:
        words = parse_words(line)
        if not words:
            return
        self._apply_modal_codes(words)
        if any(axis in words for axis in AXES):
            self._move(words)

    def _apply_modal_codes(self, words: dict[str, float]) -> None:
        # G antes de F: a linha "G20 F10" deve interpretar F já em polegadas
        if "G" in words:
            self._apply_g_code(int(words["G"]))
        if "F" in words:
            self.feed = words["F"] * self.unit_scale

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

    def _line(self, end: Point) -> None:
        if end == self.position:
            return
        self.moves.append(Move(
            start=self.position,
            end=end,
            is_cut=self.motion != G_RAPID,
            feed=self.feed,
        ))

    def _arc(self, end: Point, words: dict[str, float]) -> None:
        if "R" in words:
            raise GCodeError("arco com R não suportado; use I/J")

        start = self.position
        center = (
            start[0] + words.get("I", 0.0) * self.unit_scale,
            start[1] + words.get("J", 0.0) * self.unit_scale,
        )
        points = arc_points(start, end, center, clockwise=self.motion == G_CW_ARC)

        previous = start
        for point in points:
            self.moves.append(Move(previous, point, is_cut=True, feed=self.feed))
            previous = point