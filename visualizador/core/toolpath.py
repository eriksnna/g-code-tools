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
    head: np.ndarray  # posição da ferramenta, shape (3,)
    done: int         # movimentos concluídos
    started: int      # movimentos iniciados, incluindo o em curso


class Toolpath:
    """Movimentos com duração calculada e acumulada, prontos para consulta por tempo."""

    def __init__(self, moves: Sequence[Move], rapid_feed: float = RAPID_FEED) -> None:
        if not moves:
            raise ValueError("O caminho precisa de pelo menos um movimento.")

        self.starts = np.array([m.start for m in moves], dtype=float)
        self.ends = np.array([m.end for m in moves], dtype=float)
        self.is_cut = np.array([m.is_cut for m in moves], dtype=bool)

        feeds = np.array([m.feed if m.is_cut else rapid_feed for m in moves], dtype=float)
        feeds = np.maximum(feeds, MIN_FEED)
        lengths = np.array([m.length for m in moves], dtype=float)

        self.durations = lengths / feeds * SECONDS_PER_MINUTE
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
            return Snapshot(head=self.ends[-1].copy(), done=self.count, started=self.count)

        begin = self.cum_start[k]
        progress = (t - begin) / self.durations[k]
        head = self.starts[k] + progress * (self.ends[k] - self.starts[k])
        started = k + 1 if t > begin else k
        return Snapshot(head=head, done=k, started=started)