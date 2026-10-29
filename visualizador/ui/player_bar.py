"""Barra de reprodução. Exibe o estado e emite sinais; não decide nada sozinha."""
from __future__ import annotations

import math
from contextlib import contextmanager

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout,
)

from config import (
    SPEED_MAX, SPEED_MIN, SPEED_PRESETS, SPEED_SLIDER_SCALE, TIMELINE_STEPS,
)
from ui.theme import ACCENT, ACCENT_HOVER, SURFACE_2, TEXT_MUTED
from ui.icons import FAST_FORWARD, PAUSE, PLAY, REWIND, SKIP_BACK, SKIP_FORWARD, icon

PLAY_BUTTON_SIZE = (48, 48)
TRANSPORT_BUTTON_SIZE = (40, 40)
PRESET_BUTTON_SIZE = (46, 26)
SPEED_SLIDER_WIDTH = 160
SPEED_LABEL_WIDTH = 44


@contextmanager
def _signals_blocked(widget):
    """Atualiza um widget por código sem disparar seus sinais."""
    previous = widget.blockSignals(True)
    try:
        yield
    finally:
        widget.blockSignals(previous)

class _Slider(QSlider):
    """Slider com desenho próprio — o Fusion não respeita bem o QSS de groove no Windows."""

    TRACK_HEIGHT = 6
    HANDLE_RADIUS = 8

    def _fraction(self) -> float:
        span = max(self.maximum() - self.minimum(), 1)
        return (self.value() - self.minimum()) / span

    def _value_from_x(self, x: float) -> int:
        left = self.HANDLE_RADIUS
        right = self.width() - self.HANDLE_RADIUS
        span = max(right - left, 1)
        fraction = min(max((x - left) / span, 0.0), 1.0)
        return round(self.minimum() + fraction * (self.maximum() - self.minimum()))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        track = QRectF(
            self.HANDLE_RADIUS, self.height() / 2 - self.TRACK_HEIGHT / 2,
            self.width() - 2 * self.HANDLE_RADIUS, self.TRACK_HEIGHT,
        )
        radius = self.TRACK_HEIGHT / 2

        painter.setBrush(QColor(SURFACE_2))
        painter.drawRoundedRect(track, radius, radius)

        fraction = self._fraction()
        handle_x = track.left() + fraction * track.width()
        if fraction > 0:
            filled = QRectF(track.left(), track.top(), handle_x - track.left(), self.TRACK_HEIGHT)
            painter.setBrush(QColor(ACCENT if self.isEnabled() else TEXT_MUTED))
            painter.drawRoundedRect(filled, radius, radius)

        handle_color = ACCENT_HOVER if self.isEnabled() else TEXT_MUTED
        painter.setBrush(QColor("#ffffff" if self.isEnabled() else TEXT_MUTED))
        painter.drawEllipse(QPointF(handle_x, self.height() / 2), self.HANDLE_RADIUS, self.HANDLE_RADIUS)
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.setValue(self._value_from_x(event.position().x()))
            self.sliderPressed.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self.isEnabled():
            self.setValue(self._value_from_x(event.position().x()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.sliderReleased.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class PlayerBar(QFrame):
    play_clicked = Signal()
    start_clicked = Signal()
    end_clicked = Signal()
    step_clicked = Signal(int)     # -1 ou 1
    scrub_started = Signal()
    scrubbed = Signal(float)       # fração de 0 a 1
    speed_changed = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("playbar")

        self._timeline = _Slider(Qt.Orientation.Horizontal)
        self._timeline.setRange(0, TIMELINE_STEPS)
        self._timeline.sliderPressed.connect(self.scrub_started.emit)
        self._timeline.valueChanged.connect(
            lambda value: self.scrubbed.emit(value / TIMELINE_STEPS)
        )

        self._play_button = self._make_button(
            icon(PLAY), "Reproduzir / pausar", self.play_clicked.emit, PLAY_BUTTON_SIZE, name="play",
        )
        self._transport = [
            self._make_button(icon(SKIP_BACK), "Ir para o início", self.start_clicked.emit, TRANSPORT_BUTTON_SIZE, name="transport"),
            self._make_button(icon(REWIND), "Retroceder", lambda: self.step_clicked.emit(-1), TRANSPORT_BUTTON_SIZE, name="transport"),
            self._play_button,
            self._make_button(icon(FAST_FORWARD), "Avançar", lambda: self.step_clicked.emit(1), TRANSPORT_BUTTON_SIZE, name="transport"),
            self._make_button(icon(SKIP_FORWARD), "Ir para o fim", self.end_clicked.emit, TRANSPORT_BUTTON_SIZE, name="transport"),
        ]

        self._speed_slider = _Slider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(
            round(SPEED_MIN * SPEED_SLIDER_SCALE), round(SPEED_MAX * SPEED_SLIDER_SCALE),
        )
        self._speed_slider.setFixedWidth(SPEED_SLIDER_WIDTH)
        self._speed_slider.valueChanged.connect(self._on_speed_slider)

        self._speed_label = QLabel()
        self._speed_label.setFixedWidth(SPEED_LABEL_WIDTH)
        self._presets = [self._make_preset(value) for value in SPEED_PRESETS]

        self._status = QLabel()
        self._status.setObjectName("status")

        self._controls = [
            *self._transport, self._timeline, self._speed_slider,
            *(button for _, button in self._presets),
        ]
        self._build_layout()

    # --- montagem ---

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)
        layout.addWidget(self._timeline)
        layout.addLayout(self._build_controls_row())
        layout.addWidget(self._status)

    def _build_controls_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch()
        for widget in self._transport:
            row.addWidget(widget)
        row.addStretch()
        row.addWidget(QLabel("Velocidade"))
        row.addWidget(self._speed_slider)
        row.addWidget(self._speed_label)
        for _, button in self._presets:
            row.addWidget(button)
        return row

    @staticmethod
    def _make_button(button_icon, tip: str, callback, size, name: str | None = None) -> QPushButton:
        button = QPushButton()
        button.setIcon(button_icon)
        button.setToolTip(tip)
        button.setFixedSize(*size)
        if name:
            button.setObjectName(name)
        button.clicked.connect(lambda _checked=False: callback())
        return button

    def _make_preset(self, value: float) -> tuple[float, QPushButton]:
        button = QPushButton(f"{value:g}x")
        button.setObjectName("preset")
        button.setCheckable(True)
        button.setFixedSize(*PRESET_BUTTON_SIZE)
        button.clicked.connect(lambda _checked=False, v=value: self.speed_changed.emit(v))
        return value, button

    def _on_speed_slider(self, units: int) -> None:
        self.speed_changed.emit(units / SPEED_SLIDER_SCALE)

    # --- estado exibido (não emite sinais) ---

    def set_enabled(self, enabled: bool) -> None:
        for widget in self._controls:
            widget.setEnabled(enabled)

    def set_playing(self, playing: bool) -> None:
        self._play_button.setIcon(icon(PAUSE if playing else PLAY))

    def set_progress(self, fraction: float) -> None:
        with _signals_blocked(self._timeline):
            self._timeline.setValue(round(fraction * TIMELINE_STEPS))

    def set_speed(self, value: float) -> None:
        with _signals_blocked(self._speed_slider):
            self._speed_slider.setValue(round(value * SPEED_SLIDER_SCALE))
        self._speed_label.setText(f"{value:.1f}x")
        for preset, button in self._presets:
            button.setChecked(math.isclose(preset, value))

    def set_status(self, text: str) -> None:
        self._status.setText(text)