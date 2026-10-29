"""Controles de camadas: filtra por profundidade e liga a coloração por Z."""
from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QWidget

ALL_LAYERS_TEXT = "Todas as camadas"
COMBO_MIN_WIDTH = 140


class LayerControls(QWidget):
    filter_changed = Signal(object)          # índice da camada, ou None para todas
    depth_coloring_toggled = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._combo = QComboBox()
        self._combo.setMinimumWidth(COMBO_MIN_WIDTH)
        self._combo.currentIndexChanged.connect(self._on_index_changed)

        self._depth_check = QCheckBox("Colorir por profundidade")
        self._depth_check.toggled.connect(self.depth_coloring_toggled.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Camada"))
        layout.addWidget(self._combo)
        layout.addWidget(self._depth_check)

    def set_levels(self, levels: Sequence[float]) -> None:
        """Preenche o seletor com uma entrada por profundidade, sem disparar sinais."""
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem(ALL_LAYERS_TEXT, None)
        for index, z in enumerate(levels):
            self._combo.addItem(f"{index + 1}  ·  Z {z:g} mm", index)
        self._combo.setCurrentIndex(0)
        self._combo.blockSignals(False)
        self.setEnabled(len(levels) > 0)

    def _on_index_changed(self, index: int) -> None:
        self.filter_changed.emit(self._combo.itemData(index))