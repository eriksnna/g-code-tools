"""Tela de Ajustes: navegação lateral com seções (Perfis, Atalhos, ...)."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.machine_profile import DEFAULT_LIMITS, MachineProfile, default_profiles

SHORTCUTS_TEXT = """\
Ctrl+Return      Aplicar o G-code editado
Ctrl+/           Comentar/descomentar linha(s) selecionadas
Ctrl+S           Salvar
Ctrl+Shift+S     Salvar como...
"""


class _ProfilesPage(QWidget):
    """Lista de perfis de máquina: selecionar, criar, remover e editar limites."""

    changed = Signal()

    def __init__(
        self,
        profiles: list[MachineProfile] | None = None,
        active_profile: MachineProfile | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._profiles: list[MachineProfile] = list(profiles) if profiles else default_profiles()
        self._active: MachineProfile = active_profile or self._profiles[0]
        self._spinboxes: dict[str, tuple[QDoubleSpinBox, QDoubleSpinBox]] = {}

        layout = QVBoxLayout(self)

        self._profile_list = QListWidget()
        for profile in self._profiles:
            self._profile_list.addItem(profile.name)
        start_row = self._profiles.index(self._active) if self._active in self._profiles else 0
        self._profile_list.setCurrentRow(start_row)
        self._profile_list.currentRowChanged.connect(self._on_profile_selected)
        layout.addWidget(QLabel("Perfil de máquina:"))
        layout.addWidget(self._profile_list)

        profile_buttons = QHBoxLayout()
        add_button = QPushButton("Novo perfil")
        add_button.clicked.connect(self._add_profile)
        remove_button = QPushButton("Remover perfil")
        remove_button.clicked.connect(self._remove_profile)
        profile_buttons.addWidget(add_button)
        profile_buttons.addWidget(remove_button)
        layout.addLayout(profile_buttons)

        limits_box = QGroupBox("Limites de curso (mm)")
        form = QFormLayout(limits_box)
        for axis in ("X", "Y", "Z"):
            lo = QDoubleSpinBox()
            hi = QDoubleSpinBox()
            for spin in (lo, hi):
                spin.setRange(-1_000_000.0, 1_000_000.0)
                spin.setDecimals(2)
                spin.valueChanged.connect(self._on_limits_edited)
            row = QHBoxLayout()
            row.addWidget(QLabel("min"))
            row.addWidget(lo)
            row.addWidget(QLabel("max"))
            row.addWidget(hi)
            form.addRow(f"{axis}:", row)
            self._spinboxes[axis] = (lo, hi)
        layout.addWidget(limits_box)
        layout.addStretch(1)

        self._load_active_into_spinboxes()

    def profiles(self) -> list[MachineProfile]:
        return self._profiles

    def current_profile(self) -> MachineProfile:
        return self._active

    def _on_profile_selected(self, row: int) -> None:
        if row < 0:
            return
        self._active = self._profiles[row]
        self._load_active_into_spinboxes()
        self.changed.emit()

    def _load_active_into_spinboxes(self) -> None:
        for axis, (lo, hi) in self._spinboxes.items():
            lo_value, hi_value = self._active.limits[axis]
            lo.blockSignals(True)
            hi.blockSignals(True)
            lo.setValue(lo_value)
            hi.setValue(hi_value)
            lo.blockSignals(False)
            hi.blockSignals(False)

    def _on_limits_edited(self) -> None:
        clone = self._active.clone()
        for axis, (lo, hi) in self._spinboxes.items():
            clone.limits[axis] = (lo.value(), hi.value())
        self._active = clone
        self._profiles[self._profile_list.currentRow()] = clone
        self.changed.emit()

    def _add_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Novo perfil", "Nome do perfil:")
        name = name.strip()
        if not ok or not name:
            return
        if any(p.name == name for p in self._profiles):
            QMessageBox.warning(self, "Nome em uso", f"Já existe um perfil chamado \"{name}\".")
            return
        profile = MachineProfile(name=name, limits=dict(DEFAULT_LIMITS))
        self._profiles.append(profile)
        self._profile_list.addItem(profile.name)
        self._profile_list.setCurrentRow(self._profile_list.count() - 1)

    def _remove_profile(self) -> None:
        if len(self._profiles) <= 1:
            QMessageBox.information(self, "Não é possível remover", "É preciso manter ao menos um perfil.")
            return
        row = self._profile_list.currentRow()
        if row < 0:
            return
        answer = QMessageBox.question(
            self, "Remover perfil",
            f"Remover o perfil \"{self._profiles[row].name}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        del self._profiles[row]
        self._profile_list.takeItem(row)
        self._profile_list.setCurrentRow(0)


class _ShortcutsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Atalhos do editor:"))
        text = QPlainTextEdit(SHORTCUTS_TEXT)
        text.setReadOnly(True)
        layout.addWidget(text)


class SettingsDialog(QDialog):
    """Diálogo de Ajustes com navegação lateral entre seções."""

    profile_changed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        profiles: list[MachineProfile] | None = None,
        active_profile: MachineProfile | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajustes")
        self.resize(560, 420)

        self._nav = QListWidget()
        self._nav.addItems(["Perfis", "Atalhos"])
        self._nav.setFixedWidth(140)
        self._nav.currentRowChanged.connect(self._on_nav_changed)

        self._pages = QStackedWidget()
        self._profiles_page = _ProfilesPage(profiles=profiles, active_profile=active_profile)
        self._profiles_page.changed.connect(self.profile_changed.emit)
        self._pages.addWidget(self._profiles_page)
        self._pages.addWidget(_ShortcutsPage())

        body = QHBoxLayout()
        body.addWidget(self._nav)
        body.addWidget(self._pages, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.clicked.connect(self.accept)

        root = QVBoxLayout(self)
        root.addLayout(body)
        root.addWidget(buttons)

        self._nav.setCurrentRow(0)

    def _on_nav_changed(self, row: int) -> None:
        self._pages.setCurrentIndex(row)

    def profiles(self) -> list[MachineProfile]:
        return self._profiles_page.profiles()

    def current_profile(self) -> MachineProfile:
        return self._profiles_page.current_profile()