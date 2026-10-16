import sys
import math
import re
from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QFileDialog, QLabel, QSlider, QFrame,
)

# -------------
# Configuração
# -------------

RAPID_FEED = 5000.0      # mm/min usados nos G0 (ajuste para a sua máquina)
DEFAULT_FEED = 300.0     # mm/min, usado se o arquivo não definir F antes do corte
CUT_WIDTH = 2.0          # espessura das linhas de corte
RAPID_WIDTH = 1.0        # espessura das linhas de avanço rápido

SPEED_MIN, SPEED_MAX = 0.1, 10.0
PRESETS = [0.5, 1.0, 1.5, 2.0, 4.0]
STEP_FRACTION = 0.05     # botões ⏪ ⏩ avançam/recuam 5% do tempo total
TIMELINE_STEPS = 1000    # resolução da timeline

# ----------------
# parser de G-code
# ----------------

WORD_RE = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")


def clean_line(raw):
    line = re.sub(r"\(.*?\)", "", raw)
    line = line.split(";", 1)[0]
    return line.strip().upper()


def parse_words(line):
    """'G1 X10 Y-2.5' -> {'G': 1.0, 'X': 10.0, 'Y': -2.5}"""
    return {letter: float(value) for letter, value in WORD_RE.findall(line)}


class GCodeParser:
    """Interpreta G-code e produz a lista ordenada de movimentos com duração."""

    ARC_STEP_DEG = 5.0  # resolução dos arcos: graus por segmento

    def __init__(self):
        self.x = self.y = self.z = 0.0
        self.absolute = True          # G90 = absoluto, G91 = incremental
        self.scale = 1.0              # 1.0 = mm, 25.4 = polegadas (G20)
        self.motion = 0               # modo modal: G0, G1, G2 ou G3
        self.feed = DEFAULT_FEED      # modo modal: avanço em mm/min
        # cada movimento: (início, fim, é_corte, duração_em_segundos)
        self.moves = []
        self.warnings = []

    def parse(self, text):
        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = clean_line(raw)
            if not line:
                continue
            try:
                self._parse_line(line)
            except ValueError as err:
                self.warnings.append(f"Linha {lineno}: {err}")
        return self

    # --- interpretação de uma linha ---

    def _parse_line(self, line):
        words = parse_words(line)
        if not words:
            return

        if "G" in words:
            code = int(words["G"])
            if code in (0, 1, 2, 3):
                self.motion = code
            elif code == 20:
                self.scale = 25.4
            elif code == 21:
                self.scale = 1.0
            elif code == 90:
                self.absolute = True
            elif code == 91:
                self.absolute = False

        if "F" in words:
            # F é em unidades/min; em G20 (polegadas) converte para mm/min
            self.feed = words["F"] * self.scale

        if not any(axis in words for axis in "XYZ"):
            return

        nx = self._target("X", self.x, words)
        ny = self._target("Y", self.y, words)
        nz = self._target("Z", self.z, words)

        if self.motion in (2, 3):
            self._arc(nx, ny, nz, words, clockwise=(self.motion == 2))
        else:
            self._linear(nx, ny, nz)

    def _target(self, axis, current, words):
        """calcula a coordenada de destino respeitando G90/G91 e unidades."""
        if axis not in words:
            return current
        value = words[axis] * self.scale
        return value if self.absolute else current + value

    def _duration(self, length, is_cut):
        """Tempo em segundos para percorrer 'length' mm na velocidade do movimento."""
        feed = max(self.feed if is_cut else RAPID_FEED, 1.0)
        return length / feed * 60.0

    # --- movimentos ---

    def _linear(self, nx, ny, nz):
        start = (self.x, self.y, self.z)
        end = (nx, ny, nz)
        if start != end:
            is_cut = self.motion != 0
            length = math.dist(start, end)
            self.moves.append((start, end, is_cut, self._duration(length, is_cut)))
        self.x, self.y, self.z = end

    def _arc(self, nx, ny, nz, words, clockwise):
        """arco no plano XY (G17) com centro dado por I/J."""
        if "R" in words:
            raise ValueError("arco com R não suportado; use I/J")

        cx = self.x + words.get("I", 0.0) * self.scale
        cy = self.y + words.get("J", 0.0) * self.scale
        r = math.hypot(self.x - cx, self.y - cy)

        a0 = math.atan2(self.y - cy, self.x - cx)
        a1 = math.atan2(ny - cy, nx - cx)

        if clockwise and a1 >= a0:
            a1 -= 2 * math.pi
        elif not clockwise and a1 <= a0:
            a1 += 2 * math.pi

        sweep = a1 - a0
        steps = max(2, int(abs(sweep) / math.radians(self.ARC_STEP_DEG)) + 1)

        prev = (self.x, self.y, self.z)
        for i in range(1, steps + 1):
            t = i / steps
            a = a0 + sweep * t
            point = (
                cx + r * math.cos(a),
                cy + r * math.sin(a),
                self.z + (nz - self.z) * t,  # Z interpolado (hélice)
            )
            length = math.dist(prev, point)
            self.moves.append((prev, point, True, self._duration(length, True)))
            prev = point

        self.x, self.y, self.z = nx, ny, nz


# ---------
# estilo
# ---------

DARK_QSS = """
QMainWindow { background: #16181d; }
QWidget#central { background: #16181d; }
QLabel { color: #e6e6e6; background: transparent; font-size: 13px; }
QLabel#fileLabel { color: #8b94a5; }
QLabel#status { color: #9aa3b2; font-family: Consolas, monospace; font-size: 12px; }
QPushButton {
    background: #2a2e38; color: #e6e6e6;
    border: 1px solid #3a3f4b; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background: #343945; }
QPushButton:pressed { background: #1f222a; }
QPushButton:disabled { color: #5a606d; }
QPushButton#play { background: #2b6cb0; border: 1px solid #3b82d0; font-size: 16px; }
QPushButton#play:hover { background: #3478c4; }
QPushButton#preset { padding: 2px 4px; font-size: 12px; }
QPushButton#preset:checked { background: #3b82d0; border: 1px solid #3b82d0; }
QFrame#playbar {
    background: #1f222a; border: 1px solid #2c303b; border-radius: 10px;
}
QSlider::groove:horizontal { height: 6px; background: #343945; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #3b82d0; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #e6e6e6; width: 14px; margin: -5px 0; border-radius: 7px;
}
QSlider:disabled::handle:horizontal { background: #5a606d; }
"""

DIM_CUT = (0.2, 0.5, 0.7, 0.35)
BRIGHT_CUT = (0.2, 0.8, 1.0, 1.0)
DIM_RAPID = (1.0, 0.35, 0.35, 0.2)
BRIGHT_RAPID = (1.0, 0.35, 0.35, 0.8)
HEAD_COLOR = (1.0, 0.85, 0.2, 1.0)


@dataclass
class Layer:
    """Um GLLinePlotItem com espessura própria, contendo parte dos movimentos."""
    item: object
    idx: np.ndarray     # índices globais dos movimentos desta camada, em ordem
    base: np.ndarray    # cores apagadas, dois vértices por movimento
    bright: np.ndarray  # cores acesas


def _fmt(seconds):
    m, s = divmod(int(round(seconds)), 60)
    return f"{m:02d}:{s:02d}"


# ----------
# interface
# ----------

class GCodeVisualizerApp(QMainWindow):

    TICK_MS = 30

    def __init__(self):
        super().__init__()
        self.setWindowTitle("visualizador de G-Code 3D")
        self.resize(1100, 800)
        self.setWindowIcon(QIcon("assets/g-code.ico"))
        self.setStyleSheet(DARK_QSS)

        self.total = 0           # número de movimentos
        self.total_time = 0.0    # tempo total de máquina, em segundos
        self.elapsed = 0.0       # tempo decorrido na simulação, em segundos
        self.speed_value = 1.0
        self.layers = []
        self.head = None
        self.seg_pts = None

        self._build_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(self.TICK_MS)
        self.timer.timeout.connect(self._tick)

        self._set_controls_enabled(False)

    # --- construção da interface ---

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # cabeçalho
        header = QHBoxLayout()
        self.btn_open = QPushButton("Abrir G-code...")
        self.btn_open.clicked.connect(self.open_gcode)
        self.file_label = QLabel("Nenhum arquivo carregado")
        self.file_label.setObjectName("fileLabel")
        header.addWidget(self.btn_open)
        header.addWidget(self.file_label, 1)
        root.addLayout(header)

        # viewport 3D
        self.view = gl.GLViewWidget()
        self.view.setCameraPosition(distance=200)
        self.view.setBackgroundColor("#16181d")
        root.addWidget(self.view, 1)

        grid = gl.GLGridItem(color=(70, 75, 85, 255))
        grid.scale(10, 10, 1)
        self.view.addItem(grid)

        # barra de reprodução
        bar = QFrame()
        bar.setObjectName("playbar")
        bar_layout = QVBoxLayout(bar)
        bar_layout.setContentsMargins(14, 10, 14, 10)
        bar_layout.setSpacing(8)

        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, TIMELINE_STEPS)
        self.timeline.valueChanged.connect(self._on_timeline)
        self.timeline.sliderPressed.connect(self._pause)
        bar_layout.addWidget(self.timeline)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.btn_start = self._make_btn("⏮", "Ir para o início", self.go_start)
        self.btn_rewind = self._make_btn("⏪", "Retroceder", lambda: self.step(-1))
        self.btn_play = self._make_btn("▶", "Reproduzir / pausar", self.toggle_play)
        self.btn_play.setObjectName("play")
        self.btn_play.setFixedSize(56, 36)
        self.btn_forward = self._make_btn("⏩", "Avançar", lambda: self.step(1))
        self.btn_end = self._make_btn("⏭", "Ir para o fim", self.go_end)

        controls.addStretch()
        for btn in (self.btn_start, self.btn_rewind, self.btn_play,
                    self.btn_forward, self.btn_end):
            controls.addWidget(btn)
        controls.addStretch()

        controls.addWidget(QLabel("Velocidade"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(int(SPEED_MIN * 10), int(SPEED_MAX * 10))
        self.speed_slider.setFixedWidth(160)
        self.speed_slider.valueChanged.connect(self._on_speed_slider)
        controls.addWidget(self.speed_slider)

        self.speed_label = QLabel("")
        self.speed_label.setFixedWidth(44)
        controls.addWidget(self.speed_label)

        self.preset_buttons = []
        for p in PRESETS:
            b = QPushButton(f"{p:g}x")
            b.setObjectName("preset")
            b.setCheckable(True)
            b.setFixedSize(46, 26)
            b.clicked.connect(lambda _=False, v=p: self._set_speed(v))
            controls.addWidget(b)
            self.preset_buttons.append(b)

        bar_layout.addLayout(controls)

        self.status = QLabel("")
        self.status.setObjectName("status")
        bar_layout.addWidget(self.status)

        root.addWidget(bar)

        self._set_speed(1.0)

    def _make_btn(self, text, tip, slot):
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setFixedSize(44, 36)
        btn.clicked.connect(slot)
        return btn

    def _set_controls_enabled(self, enabled):
        widgets = [self.btn_start, self.btn_rewind, self.btn_play,
                   self.btn_forward, self.btn_end, self.timeline,
                   self.speed_slider, *self.preset_buttons]
        for w in widgets:
            w.setEnabled(enabled)

    # --- carregamento ---

    def open_gcode(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir G-code",
            "",
            "G-code (*.nc *.gcode *.ngc *.tap);;Todos os arquivos (*)",
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError as err:
            self.status.setText(f"Erro ao abrir arquivo: {err}")
            return

        parser = GCodeParser().parse(text)
        self.load_moves(parser, path)

    def load_moves(self, parser, path):
        self._pause()
        self._clear_path()
        self.file_label.setText(path)

        if not parser.moves:
            self._set_controls_enabled(False)
            self.status.setText("Nenhum movimento encontrado no arquivo.")
            return

        moves = parser.moves
        self.total = len(moves)
        self.starts = np.array([m[0] for m in moves], dtype=float)
        self.ends = np.array([m[1] for m in moves], dtype=float)
        is_cut = np.array([m[2] for m in moves], dtype=bool)
        self.durs = np.array([m[3] for m in moves], dtype=float)

        # cum_start[i] é o instante em que o movimento i começa
        self.cum_end = np.cumsum(self.durs)
        self.cum_start = self.cum_end - self.durs
        self.total_time = float(self.cum_end[-1])
        self.elapsed = 0.0

        # todos os pontos, para o enquadramento da câmera
        self.seg_pts = np.empty((2 * self.total, 3))
        self.seg_pts[0::2] = self.starts
        self.seg_pts[1::2] = self.ends

        # uma camada por espessura: rápidos (finos) e cortes (grossos)
        self.layers = []
        all_idx = np.arange(self.total)
        for mask, width, dim, bright in (
            (~is_cut, RAPID_WIDTH, DIM_RAPID, BRIGHT_RAPID),
            (is_cut, CUT_WIDTH, DIM_CUT, BRIGHT_CUT),
        ):
            idx = all_idx[mask]
            if idx.size == 0:
                continue
            pts = np.empty((2 * idx.size, 3))
            pts[0::2] = self.starts[idx]
            pts[1::2] = self.ends[idx]
            base = np.tile(np.array(dim, dtype=float), (pts.shape[0], 1))
            bright_arr = np.tile(np.array(bright, dtype=float), (pts.shape[0], 1))
            item = gl.GLLinePlotItem(
                pos=pts, color=base, width=width, antialias=True, mode="lines",
            )
            self.view.addItem(item)
            self.layers.append(Layer(item, idx, base, bright_arr))

        self.head = gl.GLScatterPlotItem(pos=self.starts[:1], size=12, color=HEAD_COLOR)
        self.view.addItem(self.head)

        self._fit_camera()
        self._set_controls_enabled(True)
        self._seek(0.0)

    def _clear_path(self):
        for layer in self.layers:
            self.view.removeItem(layer.item)
        self.layers = []
        if self.head is not None:
            self.view.removeItem(self.head)
            self.head = None

    def _fit_camera(self):
        lo, hi = self.seg_pts.min(axis=0), self.seg_pts.max(axis=0)
        center = (lo + hi) / 2
        size = float(np.linalg.norm(hi - lo))
        self.view.opts["center"] = pg.Vector(*center)
        self.view.setCameraPosition(distance=max(size * 1.5, 50))

    # --- velocidade ---

    def _speed(self):
        return self.speed_value

    def _set_speed(self, value):
        self.speed_value = min(max(round(value, 1), SPEED_MIN), SPEED_MAX)

        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(int(round(self.speed_value * 10)))
        self.speed_slider.blockSignals(False)

        self.speed_label.setText(f"{self.speed_value:.1f}x")
        for b, p in zip(self.preset_buttons, PRESETS):
            b.setChecked(abs(p - self.speed_value) < 1e-6)
        self._refresh_status()

    def _on_speed_slider(self, value):
        self._set_speed(value / 10.0)

    # --- reprodução ---

    def toggle_play(self):
        if self.total == 0:
            return
        if self.timer.isActive():
            self._pause()
            return
        if self.elapsed >= self.total_time:
            self._seek(0.0)
        self.timer.start()
        self.btn_play.setText("⏸")

    def _pause(self):
        self.timer.stop()
        self.btn_play.setText("▶")

    def _tick(self):
        dt = self.TICK_MS / 1000.0
        t = self.elapsed + dt * self._speed()
        if t >= self.total_time:
            self._seek(self.total_time)
            self._pause()
            return
        self._seek(t)

    def step(self, direction):
        if self.total == 0:
            return
        self._pause()
        self._seek(self.elapsed + direction * STEP_FRACTION * self.total_time)

    def go_start(self):
        self._pause()
        self._seek(0.0)

    def go_end(self):
        self._pause()
        self._seek(self.total_time)

    def _on_timeline(self, value):
        # só dispara com interação do usuário (ajustes programáticos bloqueiam sinais)
        if self.total:
            self._seek(value / TIMELINE_STEPS * self.total_time)

    def _seek(self, t):
        if self.total == 0:
            return
        self.elapsed = min(max(0.0, float(t)), self.total_time)

        value = round(TIMELINE_STEPS * self.elapsed / self.total_time)
        self.timeline.blockSignals(True)
        self.timeline.setValue(value)
        self.timeline.blockSignals(False)

        self._render()

    def _render(self):
        t = self.elapsed
        k = int(np.searchsorted(self.cum_end, t, side="right"))  # movimento em curso

        if k >= self.total:
            head = self.ends[-1]
            upto = self.total
        else:
            # posição interpolada dentro do movimento em curso
            f = (t - self.cum_start[k]) / self.durs[k]
            head = self.starts[k] + f * (self.ends[k] - self.starts[k])
            # o movimento em curso acende assim que começa
            upto = k + 1 if t > self.cum_start[k] else k

        for layer in self.layers:
            done = int(np.searchsorted(layer.idx, upto, side="left"))
            colors = layer.base.copy()
            colors[: 2 * done] = layer.bright[: 2 * done]
            layer.item.setData(color=colors)

        self.head.setData(pos=np.asarray(head, dtype=float).reshape(1, 3))
        self._refresh_status()

    def _refresh_status(self):
        if self.total == 0:
            return
        n = min(int(np.searchsorted(self.cum_end, self.elapsed, side="right")), self.total)
        self.status.setText(
            f"movimento {n}/{self.total}   |   "
            f"tempo {_fmt(self.elapsed)} / {_fmt(self.total_time)}   |   "
            f"velocidade {self._speed():.1f}x"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = GCodeVisualizerApp()
    window.show()
    sys.exit(app.exec())