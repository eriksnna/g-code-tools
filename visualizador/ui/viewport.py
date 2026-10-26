"""Viewport 3D: desenha o caminho, aplica cores por profundidade e o estado da simulação."""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl

from config import (
    CAMERA_MARGIN, CAMERA_MIN_DISTANCE, CAMERA_START_DISTANCE,
    CUT_WIDTH, HEAD_SIZE, RAPID_WIDTH,
)
from core.layers import layer_indices
from core.toolpath import Snapshot, Toolpath, interleave
from ui.theme import (
    ARC_HEAD_COLOR, BACKGROUND, BRIGHT_CUT, BRIGHT_RAPID, CUT_DEPTH_ALPHA, DEPTH_STOPS,
    DIM_CUT, DIM_RAPID, GRID_COLOR, HEAD_COLOR,
)

GRID_SCALE = 10


def depth_gradient(count: int) -> np.ndarray:
    """Uma cor RGB por camada, interpolada entre DEPTH_STOPS (índice 0 = mais fundo)."""
    stops = np.asarray(DEPTH_STOPS, dtype=float)
    positions = np.linspace(0.0, 1.0, len(stops))
    t = np.linspace(0.0, 1.0, count) if count > 1 else np.zeros(1)
    return np.column_stack([np.interp(t, positions, stops[:, c]) for c in range(3)])


class ToolpathView(gl.GLViewWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCameraPosition(distance=CAMERA_START_DISTANCE)
        self.setBackgroundColor(BACKGROUND)

        grid = gl.GLGridItem(color=GRID_COLOR)
        grid.scale(GRID_SCALE, GRID_SCALE, 1)
        self.addItem(grid)

        self._toolpath: Toolpath | None = None
        self._is_cut = np.empty(0, dtype=bool)
        self._levels = np.empty(0)
        self._layer_of = np.empty(0, dtype=int)
        self._dim: np.ndarray | None = None
        self._bright: np.ndarray | None = None
        self._cut_item: gl.GLLinePlotItem | None = None
        self._rapid_item: gl.GLLinePlotItem | None = None
        self._head: gl.GLScatterPlotItem | None = None

        self._depth_coloring = False
        self._layer_filter: int | None = None
        self._snapshot: Snapshot | None = None

    # --- carregamento ---

    def show_toolpath(self, toolpath: Toolpath, levels: Sequence[float]) -> None:
        self.clear()
        self._toolpath = toolpath
        self._is_cut = toolpath.is_cut
        self._levels = np.asarray(levels, dtype=float)
        self._layer_of = layer_indices(toolpath, self._levels)
        self._layer_filter = None
        self._build_colors()

        self._cut_item = self._make_line(toolpath, toolpath.is_cut, CUT_WIDTH)
        self._rapid_item = self._make_line(toolpath, ~toolpath.is_cut, RAPID_WIDTH)
        self._head = gl.GLScatterPlotItem(
            pos=toolpath.starts[:1], size=HEAD_SIZE, color=HEAD_COLOR,
        )
        self.addItem(self._head)
        self._fit_camera(toolpath)

    def clear(self) -> None:
        for item in (self._cut_item, self._rapid_item, self._head):
            if item is not None:
                self.removeItem(item)
        self._cut_item = self._rapid_item = self._head = None
        self._toolpath = None
        self._snapshot = None

    def _make_line(self, toolpath: Toolpath, mask: np.ndarray, width: float):
        if not mask.any():
            return None
        points = interleave(toolpath.starts[mask], toolpath.ends[mask])
        item = gl.GLLinePlotItem(
            pos=points, color=np.zeros((len(points), 4)),
            width=width, antialias=True, mode="lines",
        )
        self.addItem(item)
        return item

    # --- opções de visualização ---

    def set_depth_coloring(self, enabled: bool) -> None:
        self._depth_coloring = enabled
        self._build_colors()
        self._redraw()

    def set_layer_filter(self, index: int | None) -> None:
        """Mostra só os cortes de uma camada; None mostra todas."""
        self._layer_filter = index
        self._redraw()

    # --- renderização ---

    def render(self, snapshot: Snapshot) -> None:
        self._snapshot = snapshot
        if self._toolpath is None:
            return

        lit = np.arange(self._toolpath.count) < snapshot.started
        colors = np.where(lit[:, None], self._bright, self._dim)

        if self._layer_filter is not None:
            hidden = self._is_cut & (self._layer_of != self._layer_filter)
            colors[hidden, 3] = 0.0

        self._set_item_colors(self._cut_item, colors, self._is_cut)
        self._set_item_colors(self._rapid_item, colors, ~self._is_cut)
        if self._head is not None:
            color = ARC_HEAD_COLOR if snapshot.active else HEAD_COLOR
            self._head.setData(
                pos=snapshot.head.reshape(1, 3),
                color=np.asarray([color], dtype=float),
            )

    @staticmethod
    def _set_item_colors(item, colors: np.ndarray, mask: np.ndarray) -> None:
        if item is not None:
            # cada movimento tem dois vértices; a cor vale para os dois
            item.setData(color=np.repeat(colors[mask], 2, axis=0))

    def _redraw(self) -> None:
        if self._snapshot is not None:
            self.render(self._snapshot)

    def _build_colors(self) -> None:
        """Cores de cada movimento, uma vez por carregamento ou troca de modo."""
        if self._toolpath is None:
            return
        count = self._toolpath.count
        dim = np.tile(np.asarray(DIM_RAPID, dtype=float), (count, 1))
        bright = np.tile(np.asarray(BRIGHT_RAPID, dtype=float), (count, 1))

        cut = self._is_cut
        if self._depth_coloring and self._levels.size:
            rgb = depth_gradient(self._levels.size)[self._layer_of[cut]]
            dim[cut] = np.column_stack([rgb, np.full(len(rgb), CUT_DEPTH_ALPHA)])
            bright[cut] = np.column_stack([rgb, np.ones(len(rgb))])
        else:
            dim[cut] = DIM_CUT
            bright[cut] = BRIGHT_CUT

        self._dim, self._bright = dim, bright

    def _fit_camera(self, toolpath: Toolpath) -> None:
        lo, hi = toolpath.bounds()
        center = (lo + hi) / 2
        size = float(np.linalg.norm(hi - lo))
        self.opts["center"] = pg.Vector(*center)
        self.setCameraPosition(distance=max(size * CAMERA_MARGIN, CAMERA_MIN_DISTANCE))