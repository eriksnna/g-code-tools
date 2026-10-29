"""Tela de Ajustes: navegação lateral com seções (Perfis, Atalhos, ...).

Cada perfil reúne modo de processo, dialeto e limites de curso: a configuração
completa de uma máquina.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
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

from core.dialect import DIALECT_CHOICES
from core.machine_profile import DEFAULT_LIMITS, MachineProfile, default_profiles
from core.modes import MODE_CHOICES

SHORTCUTS_TEXT = """\
Ctrl+F           Buscar texto no editor
Ctrl+Return      Aplicar o G-code editado
Ctrl+/           Comentar/descomentar linha(s) selecionadas
Ctrl+S           Salvar
Ctrl+Shift+S     Salvar como...
"""


class _ProfilesPage(QWidget):
    """Lista de perfis: cada perfil reúne modo, dialeto e limites de curso."""

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
        self._loading = False

        layout = QVBoxLayout(self)

        self._profile_combo = QComboBox()
        for profile in self._profiles:
            self._profile_combo.addItem(profile.name)
        start_row = self._profiles.index(self._active) if self._active in self._profiles else 0
        self._profile_combo.setCurrentIndex(start_row)
        self._profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        layout.addWidget(QLabel("Perfil de máquina:"))
        layout.addWidget(self._profile_combo)

        profile_buttons = QHBoxLayout()
        add_button = QPushButton("Salvar como novo perfil...")
        add_button.clicked.connect(self._add_profile)
        remove_button = QPushButton("Remover perfil")
        remove_button.clicked.connect(self._remove_profile)
        profile_buttons.addWidget(add_button)
        profile_buttons.addWidget(remove_button)
        layout.addLayout(profile_buttons)

        config_box = QGroupBox("Configuração do perfil")
        form = QFormLayout(config_box)

        self._mode_combo = QComboBox()
        for label, key in MODE_CHOICES:
            self._mode_combo.addItem(label, key)
        self._mode_combo.currentIndexChanged.connect(self._on_fields_edited)
        form.addRow("Modo:", self._mode_combo)

        self._dialect_combo = QComboBox()
        for label, key in DIALECT_CHOICES:
            self._dialect_combo.addItem(label, key)
        self._dialect_combo.currentIndexChanged.connect(self._on_fields_edited)
        form.addRow("Dialeto:", self._dialect_combo)

        layout.addWidget(config_box)

        limits_box = QGroupBox("Limites de curso (mm)")
        limits_form = QFormLayout(limits_box)
        for axis in ("X", "Y", "Z"):
            lo = QDoubleSpinBox()
            hi = QDoubleSpinBox()
            for spin in (lo, hi):
                spin.setRange(-1_000_000.0, 1_000_000.0)
                spin.setDecimals(2)
                spin.valueChanged.connect(self._on_fields_edited)
            row = QHBoxLayout()
            row.addWidget(QLabel("min"))
            row.addWidget(lo)
            row.addWidget(QLabel("max"))
            row.addWidget(hi)
            limits_form.addRow(f"{axis}:", row)
            self._spinboxes[axis] = (lo, hi)

        layout.addWidget(limits_box)

        advanced_box = QGroupBox("Avançado")
        advanced_form = QFormLayout(advanced_box)

        self._rapid_feed_spin = QDoubleSpinBox()
        self._rapid_feed_spin.setRange(1.0, 100_000.0)
        self._rapid_feed_spin.setDecimals(1)
        self._rapid_feed_spin.setSuffix(" mm/min")
        self._rapid_feed_spin.valueChanged.connect(self._on_fields_edited)
        advanced_form.addRow("Avanço rápido:", self._rapid_feed_spin)

        self._default_feed_spin = QDoubleSpinBox()
        self._default_feed_spin.setRange(1.0, 100_000.0)
        self._default_feed_spin.setDecimals(1)
        self._default_feed_spin.setSuffix(" mm/min")
        self._default_feed_spin.valueChanged.connect(self._on_fields_edited)
        advanced_form.addRow("Avanço padrão:", self._default_feed_spin)

        self._min_feed_spin = QDoubleSpinBox()
        self._min_feed_spin.setRange(0.1, 10_000.0)
        self._min_feed_spin.setDecimals(2)
        self._min_feed_spin.setSuffix(" mm/min")
        self._min_feed_spin.valueChanged.connect(self._on_fields_edited)
        advanced_form.addRow("Avanço mínimo:", self._min_feed_spin)

        self._arc_step_spin = QDoubleSpinBox()
        self._arc_step_spin.setRange(0.1, 45.0)
        self._arc_step_spin.setDecimals(1)
        self._arc_step_spin.setSuffix("°")
        self._arc_step_spin.valueChanged.connect(self._on_fields_edited)
        advanced_form.addRow("Resolução de arco:", self._arc_step_spin)

        layout.addWidget(advanced_box)
        layout.addStretch(1)

        self._load_active_into_fields()

    def profiles(self) -> list[MachineProfile]:
        return self._profiles

    def current_profile(self) -> MachineProfile:
        return self._active

    def _on_profile_selected(self, row: int) -> None:
        if row < 0:
            return
        self._active = self._profiles[row]
        self._load_active_into_fields()
        self.changed.emit()

    def _load_active_into_fields(self) -> None:
        self._loading = True
        self._mode_combo.setCurrentIndex(max(0, self._mode_combo.findData(self._active.mode_key)))
        self._dialect_combo.setCurrentIndex(
            max(0, self._dialect_combo.findData(self._active.dialect_key))
        )
        for axis, (lo, hi) in self._spinboxes.items():
            lo_value, hi_value = self._active.limits[axis]
            lo.setValue(lo_value)
            hi.setValue(hi_value)
        self._rapid_feed_spin.setValue(self._active.rapid_feed)
        self._default_feed_spin.setValue(self._active.default_feed)
        self._min_feed_spin.setValue(self._active.min_feed)
        self._arc_step_spin.setValue(self._active.arc_step_deg)
        self._loading = False

    def _on_fields_edited(self) -> None:
        if self._loading:
            return
        self._active.mode_key = self._mode_combo.currentData()
        self._active.dialect_key = self._dialect_combo.currentData()
        for axis, (lo, hi) in self._spinboxes.items():
            self._active.limits[axis] = (lo.value(), hi.value())
        self._active.rapid_feed = self._rapid_feed_spin.value()
        self._active.default_feed = self._default_feed_spin.value()
        self._active.min_feed = self._min_feed_spin.value()
        self._active.arc_step_deg = self._arc_step_spin.value()
        self.changed.emit()

    def _add_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Salvar como novo perfil", "Nome do perfil:")
        name = name.strip()
        if not ok or not name:
            return
        if any(p.name == name for p in self._profiles):
            QMessageBox.warning(self, "Nome em uso", f"Já existe um perfil chamado \"{name}\".")
            return
        profile = self._active.clone()
        profile.name = name
        self._profiles.append(profile)
        self._profile_combo.addItem(profile.name)
        self._profile_combo.setCurrentIndex(self._profile_combo.count() - 1)

    def _remove_profile(self) -> None:
        if len(self._profiles) <= 1:
            QMessageBox.information(self, "Não é possível remover", "É preciso manter ao menos um perfil.")
            return
        row = self._profile_combo.currentIndex()
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
        self._profile_combo.removeItem(row)
        self._profile_combo.setCurrentIndex(0)


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
        self.resize(560, 460)

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