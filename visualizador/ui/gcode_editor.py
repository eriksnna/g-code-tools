"""Editor de texto do programa G-code carregado. 'Aplicar' reinterpreta o texto editado."""
from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor, QFont, QKeySequence, QPainter, QShortcut, QTextCharFormat, QTextCursor,
)
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from ui.gcode_highlighter import GCodeHighlighter

EDITOR_FONT_FAMILY = "Consolas"
EDITOR_FONT_SIZE = 12
APPLY_SHORTCUT = "Ctrl+Return"
COMMENT_SHORTCUT = "Ctrl+/"
SAVE_SHORTCUT = "Ctrl+S"
SAVE_AS_SHORTCUT = "Ctrl+Shift+S"
PLACEHOLDER = "Abra um arquivo G-code para editar aqui."
GUTTER_PADDING = 12
GUTTER_BACKGROUND = QColor("#191b21")
GUTTER_TEXT = QColor("#555c6b")
CURRENT_LINE_BACKGROUND = QColor("#23262f")

SHORTCUTS_TEXT = (
    f"{APPLY_SHORTCUT}   Aplicar as alterações e reinterpretar o programa\n"
    f"{COMMENT_SHORTCUT}   Comentar ou descomentar a linha atual (ou a seleção)\n"
    f"{SAVE_SHORTCUT}   Salvar no arquivo aberto\n"
    f"{SAVE_AS_SHORTCUT}   Salvar como... (escolher um novo arquivo)"
)


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

    def toggle_comment(self) -> None:
        """Comenta ou descomenta as linhas tocadas pela seleção (ou a linha do cursor).

        Usa ';' por simplicidade e por funcionar em qualquer dialeto de G-code.
        Se a primeira linha do bloco já está comentada, descomenta todas; senão, comenta todas.
        """
        cursor = self.textCursor()
        start_block = self.document().findBlock(cursor.selectionStart()).blockNumber()
        end_block = self.document().findBlock(cursor.selectionEnd()).blockNumber()

        first_text = self.document().findBlockByNumber(start_block).text()
        should_uncomment = first_text.lstrip().startswith(";")

        edit_cursor = QTextCursor(self.document())
        edit_cursor.beginEditBlock()
        for number in range(start_block, end_block + 1):
            block = self.document().findBlockByNumber(number)
            line_cursor = QTextCursor(block)
            text = block.text()
            if should_uncomment:
                stripped = text.lstrip()
                if stripped.startswith(";"):
                    indent = text[: len(text) - len(stripped)]
                    rest = stripped[1:]
                    rest = rest[1:] if rest.startswith(" ") else rest
                    line_cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                    line_cursor.insertText(indent + rest)
            elif text.strip():
                indent = text[: len(text) - len(text.lstrip())]
                line_cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                line_cursor.insertText(f"{indent}; {text.strip()}")
        edit_cursor.endEditBlock()

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
    save_requested = Signal(str)   # texto atual, quando o usuário pede para salvar no disco
    save_as_requested = Signal(str)  # texto atual, quando o usuário pede "salvar como"

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

        self._save_button = QPushButton("Salvar")
        self._save_button.setObjectName("saveEdit")
        self._save_button.clicked.connect(self._emit_save)

        self._save_as_button = QPushButton("Salvar como...")
        self._save_as_button.setObjectName("saveAsEdit")
        self._save_as_button.clicked.connect(self._emit_save_as)

        self._help_button = QPushButton("?")
        self._help_button.setObjectName("editorHelp")
        self._help_button.setFixedWidth(28)
        self._help_button.setToolTip("Atalhos do editor")
        self._help_button.clicked.connect(self._show_shortcuts)

        QShortcut(QKeySequence(APPLY_SHORTCUT), self._text_edit).activated.connect(self._emit_apply)
        QShortcut(QKeySequence(COMMENT_SHORTCUT), self._text_edit).activated.connect(
            self._text_edit.toggle_comment
        )
        QShortcut(QKeySequence(SAVE_SHORTCUT), self._text_edit).activated.connect(self._emit_save)
        QShortcut(QKeySequence(SAVE_AS_SHORTCUT), self._text_edit).activated.connect(self._emit_save_as)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(QLabel("EDITOR DE G-CODE"))
        toolbar.addWidget(self._status_label)
        toolbar.addStretch()
        toolbar.addWidget(self._help_button)
        toolbar.addWidget(self._save_button)
        toolbar.addWidget(self._save_as_button)
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

    def is_modified(self) -> bool:
        """True se o texto do editor difere do que foi carregado ou aplicado por último."""
        return self._text_edit.document().isModified()

    def goto_line(self, line: int) -> None:
        """Mostra o editor, se escondido, e vai até a linha (1-based)."""
        self.setVisible(True)
        self._text_edit.goto_line(line)

    def _emit_apply(self) -> None:
        self.apply_requested.emit(self.text())

    def _emit_save(self) -> None:
        self.save_requested.emit(self.text())

    def _emit_save_as(self) -> None:
        self.save_as_requested.emit(self.text())

    def _on_modified(self, modified: bool) -> None:
        self._status_label.setText("não aplicado" if modified else "")

    def _show_shortcuts(self) -> None:
        QMessageBox.information(self, "Atalhos do editor", SHORTCUTS_TEXT)