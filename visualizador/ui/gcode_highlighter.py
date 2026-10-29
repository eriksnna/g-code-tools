"""Realce de sintaxe para G-code: comentários, G/M-codes, eixos, variáveis e sub-rotinas."""
from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

# Ordem importa: comentários são aplicados por último, para cobrir qualquer coisa dentro deles.
COMMENT_PAREN_RE = QRegularExpression(r"\([^)]*\)")
COMMENT_SEMI_RE = QRegularExpression(r";.*$")
SUBROUTINE_LABEL_RE = QRegularExpression(r"^\s*O\d+\b")
G_CODE_RE = QRegularExpression(r"\bG\d+(\.\d+)?\b")
M_CODE_RE = QRegularExpression(r"\bM\d+\b")
AXIS_RE = QRegularExpression(r"\b[XYZIJKR][-+]?\d+(\.\d+)?\b")
FEED_SPEED_RE = QRegularExpression(r"\b[FS][-+]?\d+(\.\d+)?\b")
CALL_PARAM_RE = QRegularExpression(r"\b[PL][-+]?\d+(\.\d+)?\b")
VARIABLE_RE = QRegularExpression(r"#\d+")
NUMBER_RE = QRegularExpression(r"(?<![A-Za-z#])[-+]?\d+\.\d+\b")


def _format(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


class GCodeHighlighter(QSyntaxHighlighter):
    def __init__(self, document) -> None:
        super().__init__(document)
        self._rules = [
            (SUBROUTINE_LABEL_RE, _format("#c792ea", bold=True)),   # rótulo O1000
            (G_CODE_RE, _format("#82aaff", bold=True)),             # G1, G90...
            (M_CODE_RE, _format("#f78c6c", bold=True)),             # M8, M98...
            (AXIS_RE, _format("#c3e88d")),                          # X10, Z-5...
            (FEED_SPEED_RE, _format("#ffcb6b")),                    # F400, S1200
            (CALL_PARAM_RE, _format("#ffcb6b")),                    # P1000, L8
            (VARIABLE_RE, _format("#f07178", bold=True)),           # #1, #5
            (NUMBER_RE, _format("#89ddff")),                        # números soltos
        ]
        self._comment_format = _format("#5c6370", italic=True)

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            self._apply(pattern, text, fmt)
        self._highlight_comments(text)

    def _apply(self, pattern: QRegularExpression, text: str, fmt: QTextCharFormat) -> None:
        it = pattern.globalMatch(text)
        while it.hasNext():
            match = it.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

    def _highlight_comments(self, text: str) -> None:
        """Comentários sobrepõem qualquer outro realce que caia dentro deles."""
        it = COMMENT_PAREN_RE.globalMatch(text)
        while it.hasNext():
            match = it.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), self._comment_format)

        semi_match = COMMENT_SEMI_RE.match(text)
        if semi_match.hasMatch():
            start = semi_match.capturedStart()
            self.setFormat(start, len(text) - start, self._comment_format)