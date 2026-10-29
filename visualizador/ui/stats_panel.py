"""Painel lateral com o resumo do programa e o andamento da simulação."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout,
)

from core.stats import ProgramStats, format_duration, format_length

from core.modes.base import ModeCard

PANEL_MIN_WIDTH = 180
PROGRESS_STEPS = 1000
EMPTY_VALUE = "—"
VALUE_MIN_PX = 12
VALUE_MAX_PX = 18
VALUE_PX_DIVISOR = 11  # fonte = largura do cartão / divisor, dentro dos limites acima


class StatCard(QFrame):
    """Cartão com título, valor em destaque e detalhe opcional. Adapta a fonte à largura."""

    def __init__(self, title: str, wide: bool = False) -> None:
        super().__init__()
        self.setObjectName("card")
        self.wide = wide
        self._font_px = 0

        self._title = QLabel(title.upper())
        self._title.setObjectName("cardTitle")
        self._title.setWordWrap(True)

        self._value = QLabel(EMPTY_VALUE)
        self._value.setObjectName("cardValue")
        self._value.setWordWrap(True)

        self._detail = QLabel()
        self._detail.setObjectName("cardDetail")
        self._detail.setWordWrap(True)
        self._detail.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(2)
        layout.addWidget(self._title)
        layout.addWidget(self._value)
        layout.addWidget(self._detail)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def set_value(self, text: str, detail: str = "") -> None:
        self._value.setText(text)
        self._detail.setText(detail)
        self._detail.setVisible(bool(detail))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_value_font()

    def _fit_value_font(self) -> None:
        px = max(VALUE_MIN_PX, min(VALUE_MAX_PX, self.width() // VALUE_PX_DIVISOR))
        if px != self._font_px:
            self._font_px = px
            self._value.setStyleSheet(f"font-size: {px}px;")


def _section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label

def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())

def _card_grid(cards: list[StatCard]) -> QGridLayout:
    """Organiza os cartões em duas colunas; cartões 'wide' ocupam a linha inteira."""
    grid = QGridLayout()
    grid.setSpacing(8)
    row = col = 0
    for card in cards:
        span = 2 if card.wide else 1
        if col + span > 2:
            row, col = row + 1, 0
        grid.addWidget(card, row, col, 1, span)
        col += span
        if col == 2:
            row, col = row + 1, 0
    return grid


class StatsPanel(QFrame):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statsPanel")
        self.setMinimumWidth(PANEL_MIN_WIDTH)

        self._program = {
            "total_time": StatCard("Tempo total"),
            "layers": StatCard("Camadas"),
            "cut_time": StatCard("Tempo de corte"),
            "rapid_time": StatCard("Tempo rápido"),
            "cut_length": StatCard("Trajeto de corte"),
            "rapid_length": StatCard("Trajeto rápido"),
            "moves": StatCard("Comandos de movimento", wide=True),
            "size": StatCard("Dimensões (mm)", wide=True),
        }

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, PROGRESS_STEPS)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(8)
        self._progress = {
            "percent": StatCard("Concluído"),
            "current": StatCard("Movimento"),
            "elapsed": StatCard("Decorrido"),
            "remaining": StatCard("Restante"),
        }

        self._mode_title = _section_title("Modo")
        self._mode_box = QVBoxLayout()

        self._build_layout()
        self.clear()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        layout.addWidget(_section_title("Resumo do programa"))
        layout.addLayout(_card_grid(list(self._program.values())))

        layout.addWidget(self._mode_title)
        layout.addLayout(self._mode_box)

        layout.addWidget(_section_title("Simulação"))
        layout.addWidget(self._progress_bar)
        layout.addLayout(_card_grid(list(self._progress.values())))
        layout.addStretch()

    # --- atualização do estado exibido ---

    def clear(self) -> None:
        _clear_layout(self._mode_box)
        self._mode_title.setVisible(False)
        for card in (*self._program.values(), *self._progress.values()):
            card.set_value(EMPTY_VALUE)
        self._progress_bar.setValue(0)

    def show_program(self, stats: ProgramStats) -> None:
        p = self._program
        p["total_time"].set_value(format_duration(stats.total_time))
        p["layers"].set_value(str(stats.layer_count))
        p["cut_time"].set_value(format_duration(stats.cut_time))
        p["rapid_time"].set_value(format_duration(stats.rapid_time))
        p["cut_length"].set_value(format_length(stats.cut_length))
        p["rapid_length"].set_value(format_length(stats.rapid_length))
        p["moves"].set_value(
            f"{stats.total_moves}",
            f"{stats.cut_moves} cortes  ·  {stats.rapid_moves} rápidos",
        )

        commands = stats.commands
        breakdown = "  ·  ".join(f"{name} {n}" for name, n in commands.items() if n)
        p["moves"].set_value(
            f"{sum(commands.values())} comandos",
            f"{breakdown or 'nenhum'}  ·  {stats.total_moves} segmentos",
        )
        x, y, z = stats.size
        p["size"].set_value(
            f"{x:.1f} × {y:.1f} × {z:.1f}",
            "X × Y × Z",
        )
        
    def show_progress(self, elapsed: float, total_time: float,
                      done: int, count: int) -> None:
        fraction = elapsed / total_time if total_time > 0 else 0.0
        self._progress_bar.setValue(round(fraction * PROGRESS_STEPS))

        g = self._progress
        g["percent"].set_value(f"{fraction * 100:.0f}%")
        g["current"].set_value(f"{done} / {count}")
        g["elapsed"].set_value(format_duration(elapsed))
        g["remaining"].set_value(format_duration(max(0.0, total_time - elapsed)))

    def show_mode(self, title: str, cards: list[ModeCard]) -> None:
        _clear_layout(self._mode_box)
        self._mode_title.setText(f"Modo: {title}".upper())
        self._mode_title.setVisible(True)
        if not cards:
            return
        stat_cards = []
        for card in cards:
            widget = StatCard(card.title)
            widget.set_value(card.value, card.detail)
            stat_cards.append(widget)
        self._mode_box.addLayout(_card_grid(stat_cards))