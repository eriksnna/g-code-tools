"""Seletor de modo e parâmetros do cordão. Os campos de cordão aparecem só na deposição."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QWidget

from config import BEAD_HEIGHT_MM, BEAD_WIDTH_MM, DEFAULT_MODE, DEPOSIT_DENSITY_G_CM3
from core.modes import MODE_CHOICES, create_mode
from core.modes.base import ProcessMode
from core.modes.deposition import BeadSpec, DepositionMode

SPIN_WIDTH = 100


class ModeControls(QWidget):
    changed = Signal()  # emitido só quando o modo ou um parâmetro realmente muda

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._combo = QComboBox()
        for label, key in MODE_CHOICES:
            self._combo.addItem(label, key)
        self._combo.setCurrentIndex(max(0, self._combo.findData(DEFAULT_MODE)))

        self._width = self._make_spin(0.5, 50.0, BEAD_WIDTH_MM, " mm")
        self._height = self._make_spin(0.1, 20.0, BEAD_HEIGHT_MM, " mm")
        self._density = self._make_spin(0.1, 30.0, DEPOSIT_DENSITY_G_CM3, " g/cm³")
        self._bead_fields = [
            (QLabel("Largura"), self._width),
            (QLabel("Altura"), self._height),
            (QLabel("Densidade"), self._density),
        ]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Modo"))
        layout.addWidget(self._combo)
        for label, spin in self._bead_fields:
            layout.addWidget(label)
            layout.addWidget(spin)

        self._combo.currentIndexChanged.connect(self._on_mode_changed)
        self._update_visibility()
        self._signature = self._current_signature()

    def current_mode(self) -> ProcessMode:
        bead = BeadSpec(self._width.value(), self._height.value(), self._density.value())
        return create_mode(self._combo.currentData(), bead)

    def _make_spin(self, low: float, high: float, value: float, suffix: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setDecimals(2)
        spin.setSingleStep(0.1)
        spin.setValue(value)
        spin.setSuffix(suffix)
        spin.setFixedWidth(SPIN_WIDTH)
        spin.editingFinished.connect(self._emit_if_changed)
        return spin

    def _current_signature(self) -> tuple:
        return (self._combo.currentData(), self._width.value(),
                self._height.value(), self._density.value())

    def _emit_if_changed(self) -> None:
        signature = self._current_signature()
        if signature != self._signature:
            self._signature = signature
            self.changed.emit()

    def _on_mode_changed(self, _index: int) -> None:
        self._update_visibility()
        self._emit_if_changed()

    def _update_visibility(self) -> None:
        deposition = self._combo.currentData() == DepositionMode.key
        for label, spin in self._bead_fields:
            label.setVisible(deposition)
            spin.setVisible(deposition)