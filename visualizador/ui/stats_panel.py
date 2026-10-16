"""Painel lateral com o resumo do programa e o andamento da simulação."""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QProgressBar, QVBoxLayout

from core.stats import ProgramStats, format_duration, format_length

PANEL_WIDTH = 300
PROGRESS_STEPS = 1000
EMPTY_VALUE = "—"


class StatCard(QFrame):
    """Cartão com um título pequeno e um valor em destaque."""

    def __init__(self, title: str, wide: bool = False) -> None:
        super().__init__()
        self.setObjectName("card")
        self.wide = wide  # ocupa as duas colunas do grid

        self._value = QLabel(EMPTY_VALUE)
        self._value.setObjectName("cardValue")

        title_label = QLabel(title.upper())
        title_label.setObjectName("cardTitle")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(2)
        layout.addWidget(title_label)
        layout.addWidget(self._value)

    def set_value(self, text: str) -> None:
        self._value.setText(text)


def _section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


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
        self.setFixedWidth(PANEL_WIDTH)

        self._program = {
            "total_time": StatCard("Tempo total"),
            "layers": StatCard("Camadas"),
            "cut_time": StatCard("Tempo de corte"),
            "rapid_time": StatCard("Tempo rápido"),
            "cut_length": StatCard("Trajeto de corte"),
            "rapid_length": StatCard("Trajeto rápido"),
            "moves": StatCard("Movimentos", wide=True),
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

        self._build_layout()
        self.clear()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        layout.addWidget(_section_title("Resumo do programa"))
        layout.addLayout(_card_grid(list(self._program.values())))

        layout.addWidget(_section_title("Simulação"))
        layout.addWidget(self._progress_bar)
        layout.addLayout(_card_grid(list(self._progress.values())))
        layout.addStretch()

    # --- atualização do estado exibido ---

    def clear(self) -> None:
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
            f"{stats.total_moves}   ·   {stats.cut_moves} cortes   ·   "
            f"{stats.rapid_moves} rápidos"
        )
        width, depth, height = stats.size
        p["size"].set_value(f"{width:.1f} × {depth:.1f} × {height:.1f}")

    def show_progress(self, elapsed: float, total_time: float,
                      done: int, count: int) -> None:
        fraction = elapsed / total_time if total_time > 0 else 0.0
        self._progress_bar.setValue(round(fraction * PROGRESS_STEPS))

        g = self._progress
        g["percent"].set_value(f"{fraction * 100:.0f}%")
        g["current"].set_value(f"{done} / {count}")
        g["elapsed"].set_value(format_duration(elapsed))
        g["remaining"].set_value(format_duration(max(0.0, total_time - elapsed)))