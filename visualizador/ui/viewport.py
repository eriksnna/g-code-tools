"""Viewport 3D: desenha o caminho, aplica cores por profundidade e o estado da simulação."""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl

from config import (
    CAMERA_MARGIN, CAMERA_MIN_DISTANCE, CAMERA_START_DISTANCE,
    CUT_WIDTH, HEAD_SIZE, RAPID_WIDTH, TORCH_HEIGHT, TORCH_MAX_TILT_DEG,
    TORCH_RADIUS, WIRE_STICKOUT, WIRE_WIDTH_PX, ZOOM_MIN_DISTANCE, ZOOM_STEP,
)
from core.layers import layer_indices
from core.toolpath import Snapshot, Toolpath, interleave
from ui.theme import (
    ARC_HEAD_COLOR, BACKGROUND, BRIGHT_CUT, BRIGHT_RAPID, CUT_DEPTH_ALPHA, DEPTH_STOPS,
    DIM_CUT, DIM_RAPID, GRID_COLOR, HEAD_COLOR, TORCH_COLOR, WIRE_COLOR,
)

GRID_SCALE = 10
MIN_DIRECTION_LENGTH = 1e-6  # abaixo disso, o deslocamento XY é tratado como nulo


def depth_gradient(count: int) -> np.ndarray:
    """Uma cor RGB por camada, interpolada entre DEPTH_STOPS (índice 0 = mais fundo)."""
    stops = np.asarray(DEPTH_STOPS, dtype=float)
    positions = np.linspace(0.0, 1.0, len(stops))
    t = np.linspace(0.0, 1.0, count) if count > 1 else np.zeros(1)
    return np.column_stack([np.interp(t, positions, stops[:, c]) for c in range(3)])


def _make_torch() -> gl.GLMeshItem:
    """Cone com a ponta (bico) em z=0 e o corpo subindo em +Z, sem transformação extra."""
    mesh = gl.MeshData.cylinder(rows=1, cols=16, radius=[0.0, TORCH_RADIUS], length=TORCH_HEIGHT)
    item = gl.GLMeshItem(meshdata=mesh, color=TORCH_COLOR, smooth=True, shader="shaded", drawEdges=False)
    item.setGLOptions("opaque")
    return item


def _tilt_direction(start: np.ndarray, end: np.ndarray) -> np.ndarray | None:
    """Vetor unitário XY da direção de deslocamento, ou None se o movimento for vertical/nulo."""
    dxy = end[:2] - start[:2]
    length = float(np.linalg.norm(dxy))
    if length < MIN_DIRECTION_LENGTH:
        return None
    return dxy / length


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

        # tocha e fio: criados uma vez, escondidos até o modo deposição ativá-los
        self._show_torch = False
        self._torch_item = _make_torch()
        self._torch_item.setVisible(False)
        self.addItem(self._torch_item)

        self._wire_item = gl.GLLinePlotItem(
            pos=np.zeros((2, 3)), color=np.array([WIRE_COLOR, WIRE_COLOR]),
            width=WIRE_WIDTH_PX, antialias=True, mode="line_strip",
        )
        self._wire_item.setVisible(False)
        self.addItem(self._wire_item)

        self._last_tilt_xy = np.array([0.0, 0.0])  # direção XY mantida quando a tocha está parada

    # --- carregamento ---

    def show_toolpath(self, toolpath: Toolpath, levels: Sequence[float]) -> None:
        self.clear()
        self._toolpath = toolpath
        self._is_cut = toolpath.is_cut
        self._levels = np.asarray(levels, dtype=float)
        self._layer_of = layer_indices(toolpath, self._levels)
        self._layer_filter = None
        self._last_tilt_xy = np.array([0.0, 0.0])
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
        self._torch_item.setVisible(False)
        self._wire_item.setVisible(False)

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

    def set_show_torch(self, enabled: bool) -> None:
        """Liga ou desliga a tocha e o fio (usado no modo deposição)."""
        self._show_torch = enabled
        if not enabled:
            self._torch_item.setVisible(False)
            self._wire_item.setVisible(False)
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

        if self._show_torch:
            self._update_torch(snapshot)

    def _update_torch(self, snapshot: Snapshot) -> None:
        """Posiciona a tocha acima do ponto de trabalho, inclinada na direção do movimento."""
        head = snapshot.head
        direction = _tilt_direction(snapshot.segment_start, snapshot.segment_end)
        if direction is not None:
            self._last_tilt_xy = direction
        dx, dy = self._last_tilt_xy
        heading_deg = math.degrees(math.atan2(dy, dx)) if (dx or dy) else 0.0

        tip = head + np.array([0.0, 0.0, WIRE_STICKOUT])

        self._torch_item.resetTransform()
        # 1) move a ponta (origem local) até o ponto alvo
        self._torch_item.translate(float(tip[0]), float(tip[1]), float(tip[2]))
        # 2) gira o corpo ao redor dessa ponta: primeiro inclina (eixo Y local),
        #    depois orienta a inclinação na direção do deslocamento (eixo Z do mundo)
        self._torch_item.rotate(heading_deg, 0, 0, 1, local=False)
        self._torch_item.rotate(TORCH_MAX_TILT_DEG, 0, 1, 0, local=True)
        self._torch_item.setVisible(True)

        # o fio sempre liga a ponta real (tip, ponto fixo da rotação) ao ponto de trabalho
        self._wire_item.setData(pos=np.array([tip, head]))
        self._wire_item.setVisible(True)

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

    def wheelEvent(self, event) -> None:
        """Zoom com fator fixo por clique da roda, para manter sensibilidade em close-up."""
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = ZOOM_STEP if delta > 0 else 1.0 / ZOOM_STEP
        self.opts["distance"] = max(ZOOM_MIN_DISTANCE, self.opts["distance"] * factor)
        self.update()