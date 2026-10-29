"""Caminho da ferramenta com tempos. Converte os movimentos em arrays para a interface."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from config import MIN_FEED, RAPID_FEED
from core.parser import Move

SECONDS_PER_MINUTE = 60.0


def interleave(starts: np.ndarray, ends: np.ndarray) -> np.ndarray:
    """Intercala inícios e fins: [a0, b0, a1, b1, ...], formato do modo 'lines'."""
    points = np.empty((2 * len(starts), 3))
    points[0::2] = starts
    points[1::2] = ends
    return points


@dataclass(frozen=True)
class Snapshot:
    """Estado da simulação em um instante."""
    head: np.ndarray                 # posição da ferramenta, shape (3,)
    done: int                        # movimentos concluídos
    started: int                     # movimentos iniciados, incluindo o em curso
    active: bool = False             # processo ligado no instante
    segment_start: np.ndarray = None # início do movimento em curso (para direção/tilt)
    segment_end: np.ndarray = None   # fim do movimento em curso (para direção/tilt)

    def __post_init__(self) -> None:
        if self.segment_start is None:
            object.__setattr__(self, "segment_start", self.head)
        if self.segment_end is None:
            object.__setattr__(self, "segment_end", self.head)


class Toolpath:
    """Movimentos com duração calculada e acumulada, prontos para consulta por tempo."""

    def __init__(self, moves: Sequence[Move], rapid_feed: float = RAPID_FEED,
                 min_feed: float = MIN_FEED) -> None:
        if not moves:
            raise ValueError("O caminho precisa de pelo menos um movimento.")

        self.starts = np.array([m.start for m in moves], dtype=float)
        self.ends = np.array([m.end for m in moves], dtype=float)
        self.is_cut = np.array([m.is_cut for m in moves], dtype=bool)
        self.active = np.array([m.active for m in moves], dtype=bool)
        self.dwell = np.array([m.dwell for m in moves], dtype=float)
        self.is_dwell = self.dwell > 0
        self.rapid = np.array([m.rapid for m in moves], dtype=bool)
        # linha de origem; pode não ser crescente quando há sub-rotinas
        self.lines = np.array([m.line for m in moves], dtype=int)

        feeds = np.array([rapid_feed if m.rapid else m.feed for m in moves], dtype=float)
        feeds = np.maximum(feeds, min_feed)
        lengths = np.array([m.length for m in moves], dtype=float)
        travel = lengths / feeds * SECONDS_PER_MINUTE

        # esperas duram o tempo programado; movimentos, distância / velocidade
        self.durations = np.where(self.is_dwell, self.dwell, travel)
        self.cum_end = np.cumsum(self.durations)
        self.cum_start = self.cum_end - self.durations

    @property
    def count(self) -> int:
        return len(self.starts)

    @property
    def total_time(self) -> float:
        return float(self.cum_end[-1])

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        points = interleave(self.starts, self.ends)
        return points.min(axis=0), points.max(axis=0)

    def snapshot(self, t: float) -> Snapshot:
        """Estado da ferramenta no instante t, em segundos."""
        k = int(np.searchsorted(self.cum_end, t, side="right"))
        if k >= self.count:
            end = self.ends[-1].copy()
            return Snapshot(head=end, done=self.count, started=self.count, active=False,
                            segment_start=self.starts[-1], segment_end=end)

        begin = self.cum_start[k]
        progress = (t - begin) / self.durations[k]
        head = self.starts[k] + progress * (self.ends[k] - self.starts[k])
        started = k + 1 if t > begin else k
        return Snapshot(
            head=head, done=k, started=started, active=bool(self.active[k]),
            segment_start=self.starts[k], segment_end=self.ends[k],
        )

    def time_at_line(self, line: int) -> float | None:
        """Instante do primeiro movimento escrito na linha dada.

        Com sub-rotinas, a mesma linha pode executar várias vezes; usa-se a primeira.
        Se nenhum movimento vem dessa linha, usa o próximo escrito depois dela.
        """
        exact = np.flatnonzero(self.lines == line)
        if exact.size:
            return float(self.cum_start[exact[0]])
        later = np.flatnonzero(self.lines > line)
        if later.size == 0:
            return None
        return float(self.cum_start[later[0]])