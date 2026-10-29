"""Tela inicial: abrir um arquivo G-code existente ou começar a escrever do zero."""
from __future__ import annotations

import math

from PySide6.QtCore import QElapsedTimer, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from ui.theme import ACCENT, SURFACE_0, SURFACE_1

TITLE = "Visualizador de G-Code"
SUBTITLE = "Abra um programa existente ou escreva um novo no editor."

CONTENT_WIDTH = 360
BUTTON_WIDTH = 280
BUTTON_HEIGHT = 48
BUTTON_SPACING = 12
BLOB_TICK_MS = 50


class _LiquidBackground(QFrame):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setInterval(BLOB_TICK_MS)
        self._timer.timeout.connect(self.update)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor(SURFACE_0))

        ambient_radius = math.hypot(w, h) * 0.75
        ambient = QRadialGradient(w / 2, h / 2, ambient_radius)
        glow = QColor(SURFACE_1)
        glow.setAlpha(140)
        fade = QColor(SURFACE_0)
        fade.setAlpha(0)
        ambient.setColorAt(0.0, glow)
        ambient.setColorAt(1.0, fade)
        painter.setBrush(ambient)
        painter.drawRect(self.rect())

        t = self._clock.elapsed() / 1000.0
        blobs = [
            (0.30 + 0.08 * math.sin(t * 0.21), 0.35 + 0.06 * math.cos(t * 0.17), 0.70, ACCENT, 55),
            (0.70 + 0.07 * math.cos(t * 0.15), 0.60 + 0.08 * math.sin(t * 0.19), 0.65, SURFACE_1, 90),
            (0.50 + 0.06 * math.sin(t * 0.13 + 1.5), 0.25 + 0.05 * math.cos(t * 0.22), 0.60, ACCENT, 32),
        ]
        for cx, cy, scale, color, alpha in blobs:
            radius = max(w, h) * scale
            center_x, center_y = cx * w, cy * h
            gradient = QRadialGradient(center_x, center_y, radius)
            solid = QColor(color)
            solid.setAlpha(alpha)
            gradient.setColorAt(0.0, solid)
            faded = QColor(color)
            faded.setAlpha(0)
            gradient.setColorAt(1.0, faded)
            painter.setBrush(gradient)
            painter.drawEllipse(
                int(center_x - radius), int(center_y - radius), int(radius * 2), int(radius * 2),
            )
        painter.end()


class StartPanel(QFrame):
    open_requested = Signal()
    blank_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("startPanel")

        self._background = _LiquidBackground(self)

        title = QLabel(TITLE)
        title.setObjectName("startTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        subtitle = QLabel(SUBTITLE)
        subtitle.setObjectName("startSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        subtitle.setWordWrap(True)

        open_button = QPushButton("Abrir arquivo G-code...")
        open_button.setObjectName("startButton")
        open_button.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        open_button.clicked.connect(self.open_requested.emit)

        blank_button = QPushButton("Começar do zero")
        blank_button.setObjectName("startButtonSecondary")
        blank_button.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        blank_button.clicked.connect(self.blank_requested.emit)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(14)
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addSpacing(18)
        content_layout.addWidget(open_button, 0, Qt.AlignmentFlag.AlignHCenter)
        content_layout.addSpacing(BUTTON_SPACING)
        content_layout.addWidget(blank_button, 0, Qt.AlignmentFlag.AlignHCenter)

        content = QFrame()
        content.setObjectName("startContent")
        content.setFixedWidth(CONTENT_WIDTH)
        content.setLayout(content_layout)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()
        outer.addWidget(content, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch()

        self._background.lower()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._background.setGeometry(self.rect())