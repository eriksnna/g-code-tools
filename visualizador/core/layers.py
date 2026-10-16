"""Camadas de profundidade: agrupa os cortes pelo valor de Z. Não depende de Qt."""
from __future__ import annotations

import numpy as np

from config import LAYER_DECIMALS
from core.toolpath import Toolpath

RAPID_LAYER = -1  # índice usado para movimentos que não são corte


def depth_levels(toolpath: Toolpath) -> np.ndarray:
    """Profundidades distintas dos cortes, em ordem crescente (mais fundo primeiro)."""
    depths = toolpath.ends[toolpath.is_cut, 2]
    if depths.size == 0:
        return np.empty(0)
    return np.unique(np.round(depths, LAYER_DECIMALS))


def layer_indices(toolpath: Toolpath, levels: np.ndarray) -> np.ndarray:
    """Índice da camada de cada movimento; RAPID_LAYER para os rápidos."""
    if levels.size == 0:
        return np.full(toolpath.count, RAPID_LAYER)
    z = np.round(toolpath.ends[:, 2], LAYER_DECIMALS)
    index = np.searchsorted(levels, z)
    return np.where(toolpath.is_cut, index, RAPID_LAYER)