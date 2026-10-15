import sys
import math
import re

import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import ( 
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QFileDialog, QLabel, QSlider, QComboBox, QFrame,
)

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


def segments_to_array(segments):
    """lista de pares (ponto_a, ponto_b) -> array Nx3 para o GLLinePlotItem."""
    if not segments:
        return np.empty((0, 3))
    return np.array([p for seg in segments for p in seg], dtype=float)


class GCodeParser:
    """interpreta G-code e produz segmentos 3D."""

    ARC_STEP_DEG = 5.0  # resolução dos arcos: graus por segmento

    def __init__(self):
        self.x = self.y = self.z = 0.0
        self.absolute = True     # G90 = absoluto, G91 = incremental
        self.scale = 1.0         # 1.0 = mm, 25.4 = polegadas (G20)
        self.motion = 0          # modo modal: G0, G1, G2 ou G3
        # cada movimento: (ponto_inicial, ponto_final, é_corte), na ordem do arquivo
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
            return  # linhas como '%', 'N10' sozinho, etc.

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

        if not any(axis in words for axis in "XYZ"):
            return  # linha só de configuração ou M-codes

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

    # --- movimentos ---

    def _linear(self, nx, ny, nz):
        start = (self.x, self.y, self.z)
        end = (nx, ny, nz)
        if start != end:
            self.moves.append((start, end, self.motion != 0))
        self.x, self.y, self.z = end

    def _arc(self, nx, ny, nz, words, clockwise):
        """arco no plano XY (G17) com centro dado por I/J."""
        if "R" in words:
            raise ValueError("arco com R não suportado; use I/J")

        # I e J são offsets relativos ao ponto inicial
        cx = self.x + words.get("I", 0.0) * self.scale
        cy = self.y + words.get("J", 0.0) * self.scale
        r = math.hypot(self.x - cx, self.y - cy)

        a0 = math.atan2(self.y - cy, self.x - cx)
        a1 = math.atan2(ny - cy, nx - cx)

        # ajusta o ângulo final para o sentido correto da rotação
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
                self.z + (nz - self.z) * t,  # Z interpolado linearmente (hélice)
            )
            self.cutting.append((prev, point))
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
QPushButton#play { background: #2b6cb0; border: 1px solid #3b82d0; font-size: 16px; }
QPushButton#play:hover { background: #3478c4; }
QFrame#playbar {
    background: #1f222a; border: 1px solid #2c303b; border-radius: 10px;
}
QComboBox {
    background: #2a2e38; color: #e6e6e6;
    border: 1px solid #3a3f4b; border-radius: 6px; padding: 4px 8px; min-width: 70px;
}
QComboBox QAbstractItemView {
    background: #2a2e38; color: #e6e6e6; selection-background-color: #3b82d0;
}
QSlider::groove:horizontal { height: 6px; background: #343945; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #3b82d0; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #e6e6e6; width: 14px; margin: -5px 0; border-radius: 7px;
}
"""

DIM_CUT = (0.2, 0.5, 0.7, 0.35)
BRIGHT_CUT = (0.2, 0.8, 1.0, 1.0)
DIM_RAPID = (1.0, 0.35, 0.35, 0.2)
BRIGHT_RAPID = (1.0, 0.35, 0.35, 0.8)
HEAD_COLOR = (1.0, 0.85, 0.2, 1.0)

# ----------
# interface
# ----------

class GCodeVisualizerApp(QMainWindow):

    BASE_DURATION_S = 15.0   # tempo aproximado para reproduzir o arquivo a 1.0x
    MIN_RATE = 20.0          # segmentos por segundo, mínimo a 1.0x
    TICK_MS = 30
    SPEEDS = [0.5, 1.0, 1.5, 2.0]
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("visualizador de G-Code 3D")
        self.setWindowIcon(QIcon("assets/g-code.ico"))
        self.resize(1100, 800)
        self.setStyleSheet(DARK_QSS)

        self.total = 0           # número de movimentos
        self.position = 0.0      # progresso em movimentos (float)
        self.path_item = None
        self.head = None
        self.seg_pts = None
        self.dim_colors = None
        self.bright_colors = None

        self._build_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(self.TICK_MS)
        self.timer.timeout.connect(self._tick)

        self._set_controls_enabled(False)

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
        self.timeline.setRange(0, 0)
        self.timeline.valueChanged.connect(self._on_timeline)
        self.timeline.sliderPressed.connect(self._pause)
        bar_layout.addWidget(self.timeline)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.btn_start = self._make_btn("⏮", "Ir para o início", self.go_start)
        self.btn_rewind = self._make_btn("⏪", "Retroceder", lambda: self.step(-1))
        self.btn_play = self._make_btn("▶", "Reproduzir / pausar (Play)", self.toggle_play)
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
        self.speed = QComboBox()
        for s in self.SPEEDS:
            self.speed.addItem(f"{s:.1f}x", s)
        self.speed.setCurrentIndex(self.SPEEDS.index(1.0))
        self.speed.currentIndexChanged.connect(self._refresh_status)
        controls.addWidget(self.speed)
        bar_layout.addLayout(controls)

        self.status = QLabel("")
        self.status.setObjectName("status")
        bar_layout.addWidget(self.status)

        root.addWidget(bar)

    def _make_btn(self, text, tip, slot):
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setFixedSize(44, 36)
        btn.clicked.connect(slot)
        return btn

    def _set_controls_enabled(self, enabled):
        for w in (self.btn_start, self.btn_rewind, self.btn_play,
                  self.btn_forward, self.btn_end, self.timeline, self.speed):
            w.setEnabled(enabled)        

    def open_gcode(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "abrir G-code",
            "",
            "g-code (*.nc *.gcode *.ngc *.tap);;Todos os arquivos (*)",
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

        if not parser.moves:
            self.file_label.setText(path)
            self._set_controls_enabled(False)
            self.status.setText("Nenhum movimento encontrado no arquivo.")
            return

        self.total = len(parser.moves)
        self.position = 0.0

        # dois pontos por movimento; GLLinePlotItem em modo "lines" pareia os pontos
        self.seg_pts = np.array(
            [p for a, b, _ in parser.moves for p in (a, b)], dtype=float
        )
        is_cut = np.repeat(np.array([c for *_, c in parser.moves], dtype=bool), 2)
        self.dim_colors = np.where(is_cut[:, None], DIM_CUT, DIM_RAPID).astype(float)
        self.bright_colors = np.where(is_cut[:, None], BRIGHT_CUT, BRIGHT_RAPID).astype(float)

        self.path_item = gl.GLLinePlotItem(
            pos=self.seg_pts,
            color=self.dim_colors,
            width=2,
            antialias=True,
            mode="lines",
        )
        self.view.addItem(self.path_item)

        self.head = gl.GLScatterPlotItem(
            pos=self.seg_pts[:1],
            size=12,
            color=HEAD_COLOR,
        )
        self.view.addItem(self.head)

        self._fit_camera()

        self.timeline.blockSignals(True)
        self.timeline.setRange(0, self.total)
        self.timeline.blockSignals(False)

        self.file_label.setText(path)
        self._set_controls_enabled(True)
        self._seek(0)

    def _clear_path(self):
        for item in (self.path_item, self.head):
            if item is not None:
                self.view.removeItem(item)
        self.path_item = None
        self.head = None

    def _fit_camera(self):
        lo, hi = self.seg_pts.min(axis=0), self.seg_pts.max(axis=0)
        center = (lo + hi) / 2
        size = float(np.linalg.norm(hi - lo))
        self.view.opts["center"] = pg.Vector(*center)
        self.view.setCameraPosition(distance=max(size * 1.5, 50))

    # --- reprodução -------------------------------------------------------

    def _rate(self):
        """Movimentos por segundo a 1.0x, ajustado ao tamanho do arquivo."""
        return max(self.MIN_RATE, self.total / self.BASE_DURATION_S)

    def _speed(self):
        return self.speed.currentData()

    def toggle_play(self):
        if self.total == 0:
            return
        if self.timer.isActive():
            self._pause()
            return
        if self.position >= self.total:
            self._seek(0)
        self.timer.start()
        self.btn_play.setText("⏸")

    def _pause(self):
        self.timer.stop()
        self.btn_play.setText("▶")

    def _tick(self):
        dt = self.TICK_MS / 1000.0
        self.position += self._speed() * self._rate() * dt
        if self.position >= self.total:
            self._seek(self.total)
            self._pause()
            return
        self._seek(self.position)

    def step(self, direction):
        """Avança ou retrocede 2% do arquivo (mínimo de 1 movimento)."""
        if self.total == 0:
            return
        self._pause()
        n = max(1, self.total // 50)
        self._seek(self.position + direction * n)

    def go_start(self):
        self._pause()
        self._seek(0)

    def go_end(self):
        self._pause()
        self._seek(self.total)

    def _on_timeline(self, value):
        # chamado quando o usuário arrasta a timeline
        if self.total and int(self.position) != value:
            self._seek(value)

    def _seek(self, value):
        if self.total == 0:
            return
        self.position = min(max(0.0, float(value)), float(self.total))
        n = int(self.position)

        self.timeline.blockSignals(True)
        self.timeline.setValue(n)
        self.timeline.blockSignals(False)

        self._render(n)

    def _render(self, n):
        colors = self.dim_colors.copy()
        colors[: 2 * n] = self.bright_colors[: 2 * n]
        self.path_item.setData(color=colors)

        # ponto da cabeça: fim do último movimento executado
        head_idx = max(0, 2 * n - 1)
        self.head.setData(pos=self.seg_pts[head_idx].reshape(1, 3))

        self._refresh_status()

    def _refresh_status(self):
        if self.total == 0:
            return
        n = int(self.position)
        pct = 100.0 * n / self.total
        self.status.setText(
            f"movimento {n}/{self.total}  ({pct:.0f}%)   |   "
            f"velocidade {self._speed():.1f}x"
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = GCodeVisualizerApp()
    window.show()
    sys.exit(app.exec())