"""Painel de validação: lista os problemas e leva o usuário até a linha no caminho."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QLabel, QListWidget, QListWidgetItem, QVBoxLayout,
)

from core.parser import ERROR, Issue
from ui.theme import ERROR_COLOR, WARNING_COLOR

PANEL_WIDTH = 300
LINE_ROLE = Qt.ItemDataRole.UserRole
HINT_TEXT = "Clique em um problema para ir até a linha."
EMPTY_TEXT = "Nenhum problema encontrado."


class IssuesPanel(QFrame):
    issue_selected = Signal(int)  # número da linha

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("issuesPanel")
        self.setFixedWidth(PANEL_WIDTH)

        title = QLabel("VALIDAÇÃO")
        title.setObjectName("sectionTitle")

        self._summary = QLabel()
        self._summary.setObjectName("issueSummary")

        self._list = QListWidget()
        self._list.setObjectName("issues")
        self._list.itemClicked.connect(self._on_clicked)

        self._empty = QLabel(EMPTY_TEXT)
        self._empty.setObjectName("issueEmpty")

        self._detail = QLabel(HINT_TEXT)
        self._detail.setObjectName("issueDetail")
        self._detail.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(self._summary)
        layout.addWidget(self._list, 1)
        layout.addWidget(self._empty)
        layout.addWidget(self._detail)

        self.show_issues([])

    def show_issues(self, issues: list[Issue]) -> None:
        self._list.clear()
        for issue in issues:
            item = QListWidgetItem(f"L{issue.line}   {issue.message}")
            item.setData(LINE_ROLE, issue.line)
            color = ERROR_COLOR if issue.severity == ERROR else WARNING_COLOR
            item.setForeground(QColor(color))
            item.setToolTip(f"{issue.severity}: {issue.message}")
            self._list.addItem(item)

        errors = sum(1 for issue in issues if issue.severity == ERROR)
        warnings = len(issues) - errors
        has_issues = bool(issues)

        self._list.setVisible(has_issues)
        self._empty.setVisible(not has_issues)
        self._summary.setText(
            f"{errors} erro(s)   ·   {warnings} aviso(s)" if has_issues else ""
        )
        self._detail.setText(HINT_TEXT)

    def show_source(self, line: int, text: str) -> None:
        self._detail.setText(f"Linha {line}:  {text or '(vazia)'}")

    def _on_clicked(self, item: QListWidgetItem) -> None:
        self.issue_selected.emit(item.data(LINE_ROLE))