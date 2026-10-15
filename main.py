import sys
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
import pyqtgraph.opengl as gl


class GCodeVisualizerApp(QMainWindow):
   def __init__(self):
    super().__init__()
    self.setWindowTitle("Visualizador de G-Code 3D")
    self.resize(1024, 768)

    central_widget = QWidget()
    self.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)

    # widget 3D do PyQtGraph (OpenGL)

    self.view = gl.GLViewWidget()
    self.view.setCameraPosition(distance=200)
    layout.addWidget(self.view)

    # grade de referência
    
    grid = gl.GLGridItem()
    grid.scale(10, 10, 1)
    self.view.addItem(grid)

    self.btn_load = QPushButton("Carregar Trajeto de Teste")
    self.btn_load.clicked.connect(self.plot_mock_gcode)
    layout.addWidget(self.btn_load)

   def plot_mock_gcode(self):
       # simulação de espiral 3D usando NumPy
       t = np.linspace(0, 50, 1000)
       x = np.sin(t) * (50 - t)
       y = np.cos(t) * (50 - t)
       z = t * 2
       points = np.vstack([x, y, z]).transpose()
       line = gl.GLLinePlotItem(pos=points, color=(0.2, 0.8, 1.0, 1.0), width=2, antialias=True)
       self.view.addItem(line)

if __name__ == "__main__":
   app = QApplication(sys.argv)
   app.setStyle("Fusion")
   window = GCodeVisualizerApp()
   window.show()
   sys.exit(app.exec())