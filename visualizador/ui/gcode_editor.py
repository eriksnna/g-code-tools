"""Editor de texto do programa G-code carregado. 'Aplicar' reinterpreta o texto editado."""
from __future__ import annotations

from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)
from PySide6.QtCore import Signal

from ui.gcode_highlighter import GCodeHighlighter

EDITOR_FONT_FAMILY = "Consolas"
EDITOR_FONT_SIZE = 12
APPLY_SHORTCUT = "Ctrl+Return"
PLACEHOLDER = "Abra um arquivo G-code para editar aqui."


class GCodeEditor(QFrame):
    apply_requested = Signal(str)  # texto atual, quando o usuário pede para aplicar

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("editorPanel")

        self._text_edit = QPlainTextEdit()
        self._text_edit.setObjectName("codeEditor")
        self._text_edit.setPlaceholderText(PLACEHOLDER)
        font = QFont(EDITOR_FONT_FAMILY, EDITOR_FONT_SIZE)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text_edit.setFont(font)
        self._highlighter = GCodeHighlighter(self._text_edit.document())
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._text_edit.modificationChanged.connect(self._on_modified)

        self._status_label = QLabel("")
        self._status_label.setObjectName("editorStatus")

        self._apply_button = QPushButton("Aplicar (Ctrl+Enter)")
        self._apply_button.setObjectName("applyEdit")
        self._apply_button.clicked.connect(self._emit_apply)

        shortcut = QShortcut(QKeySequence(APPLY_SHORTCUT), self._text_edit)
        shortcut.activated.connect(self._emit_apply)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(QLabel("EDITOR DE G-CODE"))
        toolbar.addWidget(self._status_label)
        toolbar.addStretch()
        toolbar.addWidget(self._apply_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        layout.addLayout(toolbar)
        layout.addWidget(self._text_edit, 1)

    def set_text(self, text: str) -> None:
        """Carrega um novo texto, sem marcar como alterado (uso ao abrir um arquivo)."""
        self._text_edit.setPlainText(text)
        self._text_edit.document().setModified(False)

    def text(self) -> str:
        return self._text_edit.toPlainText()

    def mark_applied(self) -> None:
        """Limpa o indicador de alteração pendente, sem mudar o texto."""
        self._text_edit.document().setModified(False)

    def _emit_apply(self) -> None:
        self.apply_requested.emit(self.text())

    def _on_modified(self, modified: bool) -> None:
        self._status_label.setText("não aplicado" if modified else "")