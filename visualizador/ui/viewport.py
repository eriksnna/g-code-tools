"""Viewport 3D: desenha o caminho e a ferramenta, e aplica o estado da simulação."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl

from config import (
    CAMERA_MARGIN, CAMERA_MIN_DISTANCE, CAMERA_START_DISTANCE,
    CUT_WIDTH, HEAD_SIZE, RAPID_WIDTH,
)
from core.toolpath import Snapshot, Toolpath, interleave
from ui.theme import (
    BACKGROUND, BRIGHT_CUT, BRIGHT_RAPID, DIM_CUT, DIM_RAPID,
    GRID_COLOR, HEAD_COLOR,
)

GRID_SCALE = 10

# (é_corte, espessura, cor apagada, cor acesa)
LAYER_SPECS = (
    (False, RAPID_WIDTH, DIM_RAPID, BRIGHT_RAPID),
    (True, CUT_WIDTH, DIM_CUT, BRIGHT_CUT),
)


@dataclass
class _Layer:
    """Movimentos de um mesmo tipo, desenhados com a mesma espessura."""
    item: gl.GLLinePlotItem
    move_indices: np.ndarray  # índices globais, em ordem crescente
    dim: np.ndarray           # cores apagadas, dois vértices por movimento
    bright: np.ndarray        # cores acesas


class ToolpathView(gl.GLViewWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCameraPosition(distance=CAMERA_START_DISTANCE)
        self.setBackgroundColor(BACKGROUND)

        grid = gl.GLGridItem(color=GRID_COLOR)
        grid.scale(GRID_SCALE, GRID_SCALE, 1)
        self.addItem(grid)

        self._layers: list[_Layer] = []
        self._head: gl.GLScatterPlotItem | None = None

    def show_toolpath(self, toolpath: Toolpath) -> None:
        self.clear()
        for is_cut, width, dim, bright in LAYER_SPECS:
            self._add_layer(toolpath, is_cut, width, dim, bright)

        self._head = gl.GLScatterPlotItem(
            pos=toolpath.starts[:1], size=HEAD_SIZE, color=HEAD_COLOR,
        )
        self.addItem(self._head)
        self._fit_camera(toolpath)

    def clear(self) -> None:
        for layer in self._layers:
            self.removeItem(layer.item)
        self._layers = []
        if self._head is not None:
            self.removeItem(self._head)
            self._head = None

    def render(self, snapshot: Snapshot) -> None:
        for layer in self._layers:
            lit = int(np.searchsorted(layer.move_indices, snapshot.started, side="left"))
            colors = layer.dim.copy()
            colors[: 2 * lit] = layer.bright[: 2 * lit]
            layer.item.setData(color=colors)

        if self._head is not None:
            self._head.setData(pos=snapshot.head.reshape(1, 3))

    def _add_layer(self, toolpath: Toolpath, is_cut: bool, width: float,
                   dim: tuple, bright: tuple) -> None:
        indices = np.flatnonzero(toolpath.is_cut == is_cut)
        if indices.size == 0:
            return

        points = interleave(toolpath.starts[indices], toolpath.ends[indices])
        dim_colors = np.tile(dim, (points.shape[0], 1))
        bright_colors = np.tile(bright, (points.shape[0], 1))

        item = gl.GLLinePlotItem(
            pos=points, color=dim_colors, width=width, antialias=True, mode="lines",
        )
        self.addItem(item)
        self._layers.append(_Layer(item, indices, dim_colors, bright_colors))

    def _fit_camera(self, toolpath: Toolpath) -> None:
        lo, hi = toolpath.bounds()
        center = (lo + hi) / 2
        size = float(np.linalg.norm(hi - lo))
        self.opts["center"] = pg.Vector(*center)
        self.setCameraPosition(distance=max(size * CAMERA_MARGIN, CAMERA_MIN_DISTANCE))