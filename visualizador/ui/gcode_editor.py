"""Editor de texto do programa G-code carregado. 'Aplicar' reinterpreta o texto editado."""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor, QFont, QKeySequence, QPainter, QShortcut, QTextBlock, QTextCharFormat, QTextCursor,
)
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from ui.gcode_highlighter import GCodeHighlighter

EDITOR_FONT_FAMILY = "Consolas"
EDITOR_FONT_SIZE = 12
APPLY_SHORTCUT = "Ctrl+Return"
PLACEHOLDER = "Abra um arquivo G-code para editar aqui."
GUTTER_PADDING = 12
GUTTER_BACKGROUND = QColor("#191b21")
GUTTER_TEXT = QColor("#555c6b")
CURRENT_LINE_BACKGROUND = QColor("#23262f")


class _LineNumberGutter(QWidget):
    """Margem que desenha o número de cada linha visível do editor."""

    def __init__(self, editor: "_CodeTextEdit") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.gutter_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_gutter(event)


class _CodeTextEdit(QPlainTextEdit):
    """QPlainTextEdit com margem de números de linha e destaque da linha atual."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._gutter = _LineNumberGutter(self)
        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._update_gutter_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_gutter_width()
        self._highlight_current_line()

    def gutter_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return GUTTER_PADDING * 2 + self.fontMetrics().horizontalAdvance("9") * digits

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        rect = self.contentsRect()
        self._gutter.setGeometry(QRect(rect.left(), rect.top(), self.gutter_width(), rect.height()))

    def paint_gutter(self, event) -> None:
        painter = QPainter(self._gutter)
        painter.fillRect(event.rect(), GUTTER_BACKGROUND)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        painter.setPen(GUTTER_TEXT)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0, int(top), self._gutter.width() - GUTTER_PADDING,
                    self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def goto_line(self, line: int) -> None:
        """Move o cursor para a linha (1-based) e a centraliza na tela."""
        block = self.document().findBlockByNumber(max(0, line - 1))
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    def _update_gutter_width(self) -> None:
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _update_gutter_area(self, rect, dy: int) -> None:
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    def _highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(CURRENT_LINE_BACKGROUND)
        selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


class GCodeEditor(QFrame):
    apply_requested = Signal(str)  # texto atual, quando o usuário pede para aplicar

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("editorPanel")

        self._text_edit = _CodeTextEdit()
        self._text_edit.setObjectName("codeEditor")
        self._text_edit.setPlaceholderText(PLACEHOLDER)
        font = QFont(EDITOR_FONT_FAMILY, EDITOR_FONT_SIZE)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text_edit.setFont(font)
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._text_edit.modificationChanged.connect(self._on_modified)
        self._highlighter = GCodeHighlighter(self._text_edit.document())

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

    def goto_line(self, line: int) -> None:
        """Mostra o editor, se escondido, e vai até a linha (1-based)."""
        self.setVisible(True)
        self._text_edit.goto_line(line)

    def _emit_apply(self) -> None:
        self.apply_requested.emit(self.text())

    def _on_modified(self, modified: bool) -> None:
        self._status_label.setText("não aplicado" if modified else "")