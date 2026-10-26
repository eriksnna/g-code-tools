"""Estatísticas do programa. Calcula os números a partir do Toolpath, sem Qt."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from core.layers import depth_levels
from core.toolpath import Toolpath


@dataclass(frozen=True)
class ProgramStats:
    total_moves: int
    cut_moves: int
    rapid_moves: int
    total_time: float      # segundos
    cut_time: float        # segundos
    rapid_time: float      # segundos
    cut_length: float      # mm
    rapid_length: float    # mm
    layer_count: int
    size: tuple[float, float, float]  # dimensões da peça, mm (apenas trechos de corte)
    dwell_time: float = 0.0    # segundos de espera (G04)
    dwell_count: int = 0       # número de esperas
    active_time: float = 0.0   # segundos com o processo ligado
    commands: dict[str, int] = field(default_factory=dict)  # G0 a G4


def compute_stats(toolpath: Toolpath, commands: dict[str, int] | None = None) -> ProgramStats:
    cut = toolpath.is_cut
    dwell = toolpath.is_dwell
    rapid = ~cut & ~dwell
    lengths = np.linalg.norm(toolpath.ends - toolpath.starts, axis=1)
    durations = toolpath.durations

    return ProgramStats(
        total_moves=toolpath.count,
        cut_moves=int(cut.sum()),
        rapid_moves=int(rapid.sum()),
        total_time=toolpath.total_time,
        cut_time=float(durations[cut].sum()),
        rapid_time=float(durations[rapid].sum()),
        cut_length=float(lengths[cut].sum()),
        rapid_length=float(lengths[rapid].sum()),
        layer_count=_count_layers(toolpath),
        size=_cut_extent(toolpath),
        dwell_time=float(durations[dwell].sum()),
        dwell_count=int(dwell.sum()),
        active_time=float(durations[toolpath.active].sum()),
        commands=dict(commands or {}),
    )


def _count_layers(toolpath: Toolpath) -> int:
    return int(depth_levels(toolpath).size)


def _cut_extent(toolpath: Toolpath) -> tuple[float, float, float]:
    cut = toolpath.is_cut
    if cut.any():
        points = np.vstack([toolpath.starts[cut], toolpath.ends[cut]])
    else:
        points = np.vstack([toolpath.starts, toolpath.ends])
    extent = points.max(axis=0) - points.min(axis=0)
    return (float(extent[0]), float(extent[1]), float(extent[2]))


def format_duration(seconds: float) -> str:
    """65 -> '01:05'; 3725 -> '1:02:05'."""
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_length(mm: float) -> str:
    """Usa metros acima de 1 000 mm, para o número caber no cartão."""
    if mm >= 1000:
        return f"{mm / 1000:.2f} m"
    return f"{mm:.1f} mm"