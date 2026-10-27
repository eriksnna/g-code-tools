"""Tela inicial: abrir um arquivo G-code existente ou começar a escrever do zero."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

TITLE = "Visualizador de G-Code"
SUBTITLE = "Abra um programa existente ou escreva um novo no editor."


class StartPanel(QFrame):
    open_requested = Signal()
    blank_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("startPanel")

        title = QLabel(TITLE)
        title.setObjectName("startTitle")
        subtitle = QLabel(SUBTITLE)
        subtitle.setObjectName("startSubtitle")

        open_button = QPushButton("Abrir arquivo G-code...")
        open_button.setObjectName("startButton")
        open_button.clicked.connect(self.open_requested.emit)

        blank_button = QPushButton("Começar do zero (editor)")
        blank_button.setObjectName("startButtonSecondary")
        blank_button.clicked.connect(self.blank_requested.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(14)
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(open_button)
        layout.addWidget(blank_button)
        layout.addStretch()