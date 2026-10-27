"""Seletor de perfil de máquina e edição dos limites de curso (segurança)."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QLabel, QPushButton, QWidget,
)

from core.machine_profile import MachineProfile, default_profiles

AXIS_RANGE = (-100_000.0, 100_000.0)
COMBO_MIN_WIDTH = 160


class _LimitsDialog(QDialog):
    """Formulário simples para editar o min/max de X, Y e Z de um perfil."""

    def __init__(self, profile: MachineProfile, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Limites de curso — {profile.name}")
        self._profile = profile
        self._fields: dict[str, tuple[QDoubleSpinBox, QDoubleSpinBox]] = {}

        form = QFormLayout()
        for axis in "XYZ":
            low, high = profile.limits[axis]
            low_spin = self._make_spin(low)
            high_spin = self._make_spin(high)
            row = QHBoxLayout()
            row.addWidget(QLabel("mín"))
            row.addWidget(low_spin)
            row.addWidget(QLabel("máx"))
            row.addWidget(high_spin)
            form.addRow(f"Eixo {axis} (mm)", row)
            self._fields[axis] = (low_spin, high_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = form
        self.setLayout(layout)
        layout.addRow(buttons)

    @staticmethod
    def _make_spin(value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(*AXIS_RANGE)
        spin.setDecimals(1)
        spin.setValue(value)
        spin.setFixedWidth(100)
        return spin

    def apply_to_profile(self) -> None:
        for axis, (low_spin, high_spin) in self._fields.items():
            self._profile.limits[axis] = (low_spin.value(), high_spin.value())


class MachineControls(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._profiles = default_profiles()

        self._combo = QComboBox()
        self._combo.setMinimumWidth(COMBO_MIN_WIDTH)
        for profile in self._profiles:
            self._combo.addItem(profile.name)
        self._combo.currentIndexChanged.connect(lambda _index: self.changed.emit())

        self._edit_button = QPushButton("Limites...")
        self._edit_button.clicked.connect(self._edit_limits)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Máquina"))
        layout.addWidget(self._combo)
        layout.addWidget(self._edit_button)

    def current_profile(self) -> MachineProfile:
        return self._profiles[self._combo.currentIndex()]

    def _edit_limits(self) -> None:
        profile = self.current_profile()
        dialog = _LimitsDialog(profile, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.apply_to_profile()
            self.changed.emit()