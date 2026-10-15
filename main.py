import sys
import math
import re
from dataclasses import dataclass, field # (não utilizado diretamente)

import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtWidgets import ( 
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog, QLabel,
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
        self.cutting = []        # segmentos de corte (G1/G2/G3)
        self.rapid = []          # segmentos de avanço rápido (G0)
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
            target = self.cutting if self.motion == 1 else self.rapid
            target.append((start, end))
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

class GCodeVisualizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("visualizador de G-Code 3D")
        self.resize(1024, 768)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # widget 3D (OpenGL)
        self.view = gl.GLViewWidget()
        self.view.setCameraPosition(distance=200)
        layout.addWidget(self.view)

        # grade de referência
        grid = gl.GLGridItem()
        grid.scale(10, 10, 1)
        self.view.addItem(grid)

        self.path_items = []

        self.status = QLabel("nenhum arquivo carregado.")
        layout.addWidget(self.status)

        self.btn_load = QPushButton("abrir arquivo G-code...")
        self.btn_load.clicked.connect(self.open_gcode)
        layout.addWidget(self.btn_load)


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
        self.draw_toolpath(parser, path)

    def clear_path(self):
        for item in self.path_items:
            self.view.removeItem(item)
        self.path_items.clear()

    def draw_toolpath(self, parser, path):
        self.clear_path()
        
        all_segments = parser.cutting + parser.rapid
        if not all_segments:
            self.status.setText("nenhum movimento encontrado no arquivo.")
            return
        
        # rápidos em vermelho translúcido, cortes em azul
        if parser.rapid:
            self._add_lines(parser.rapid, color=(1.0, 0.35, 0.35, 0.6), width=1)
        if parser.cutting:
            self._add_lines(parser.cutting, color=(0.2, 0.8, 1.0, 1.0), width=2)
        
        # centraliza a câmera na peça
        pts = segments_to_array(all_segments)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        center = (lo + hi) / 2
        size = float(np.linalg.norm(hi - lo))
        self.view.opts["center"] = pg.Vector(*center)
        self.view.setCameraPosition(distance=max(size * 1.5, 50))
        
        msg = (
            f"{path}: {len(parser.cutting)} segmentos de corte, "
            f"{len(parser.rapid)} de avanço rápido"
        )
        if parser.warnings:
            msg += f" | {len(parser.warnings)} aviso(s), ex.: {parser.warnings[0]}"
        self.status.setText(msg)

    def _add_lines(self, segments, color, width):
        item = gl.GLLinePlotItem(
            pos=segments_to_array(segments),
            color=color,
            width=width,
            antialias=True,
            mode="lines",  # cada par de pontos vira um segmento independente
        )
        self.view.addItem(item)
        self.path_items.append(item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = GCodeVisualizerApp()
    window.show()
    sys.exit(app.exec())