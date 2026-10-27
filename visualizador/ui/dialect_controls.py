"""Seletor de dialeto de G-code: define a unidade do G04 e os M-codes de processo."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from config import DEFAULT_DIALECT
from core.dialect import DIALECT_CHOICES, Dialect, get_dialect

COMBO_MIN_WIDTH = 160


class DialectControls(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._combo = QComboBox()
        self._combo.setMinimumWidth(COMBO_MIN_WIDTH)
        for label, key in DIALECT_CHOICES:
            self._combo.addItem(label, key)
        self._combo.setCurrentIndex(max(0, self._combo.findData(DEFAULT_DIALECT)))
        self._combo.currentIndexChanged.connect(lambda _index: self.changed.emit())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Dialeto"))
        layout.addWidget(self._combo)

    def current_dialect(self) -> Dialect:
        return get_dialect(self._combo.currentData())