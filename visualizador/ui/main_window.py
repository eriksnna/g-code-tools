"""Janela principal: liga a interface ao modelo e ao estado de reprodução."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

from config import APP_TITLE, GCODE_FILTER, ICON_PATH, TICK_MS, WINDOW_SIZE
from core.parser import parse_gcode
from core.playback import Playback
from core.toolpath import Snapshot, Toolpath
from ui.player_bar import PlayerBar
from ui.theme import DARK_QSS
from ui.viewport import ToolpathView


def format_time(seconds: float) -> str:
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(*WINDOW_SIZE)
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setStyleSheet(DARK_QSS)

        self._toolpath: Toolpath | None = None
        self._warnings: list[str] = []
        self._playback = Playback()

        self._open_button = QPushButton("Abrir G-code...")
        self._file_label = QLabel("Nenhum arquivo carregado")
        self._file_label.setObjectName("fileLabel")
        self._viewport = ToolpathView()
        self._player = PlayerBar()

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._on_tick)
        self._frame_clock = QElapsedTimer()

        self._build_layout()
        self._connect_signals()
        self._player.set_speed(self._playback.speed)
        self._player.set_enabled(False)

    # --- montagem ---

    def _build_layout(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(self._open_button)
        header.addWidget(self._file_label, 1)

        root.addLayout(header)
        root.addWidget(self._viewport, 1)
        root.addWidget(self._player)
        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self._open_button.clicked.connect(lambda _checked=False: self.open_file())

        p = self._player
        p.play_clicked.connect(self._toggle_play)
        p.start_clicked.connect(self._go_to_start)
        p.end_clicked.connect(self._go_to_end)
        p.step_clicked.connect(self._step)
        p.scrub_started.connect(self._pause)
        p.scrubbed.connect(self._scrub_to)
        p.speed_changed.connect(self._change_speed)

    # --- carregamento ---

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Abrir G-code", "", GCODE_FILTER)
        if path:
            self.load_file(Path(path))

    def load_file(self, path: Path) -> None:
        self._pause()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as err:
            self._player.set_status(f"Erro ao abrir arquivo: {err}")
            return

        result = parse_gcode(text)
        self._file_label.setText(str(path))
        self._warnings = result.warnings

        if not result.moves:
            self._show_empty()
            return

        self._toolpath = Toolpath(result.moves)
        self._playback.reset(self._toolpath.total_time)
        self._viewport.show_toolpath(self._toolpath)
        self._player.set_enabled(True)
        self._refresh()

    def _show_empty(self) -> None:
        self._toolpath = None
        self._viewport.clear()
        self._player.set_enabled(False)
        self._player.set_status("Nenhum movimento encontrado no arquivo.")

    # --- ações de reprodução ---

    def _toggle_play(self) -> None:
        self._playback.toggle()
        self._refresh()

    def _pause(self) -> None:
        self._playback.pause()
        self._timer.stop()
        self._refresh()

    def _go_to_start(self) -> None:
        self._playback.pause()
        self._playback.seek(0.0)
        self._refresh()

    def _go_to_end(self) -> None:
        self._playback.pause()
        self._playback.seek(self._playback.total_time)
        self._refresh()

    def _step(self, direction: int) -> None:
        self._playback.step(direction)
        self._refresh()

    def _scrub_to(self, fraction: float) -> None:
        self._playback.seek_fraction(fraction)
        self._refresh()

    def _change_speed(self, value: float) -> None:
        self._playback.set_speed(value)
        self._player.set_speed(self._playback.speed)
        self._refresh()

    def _on_tick(self) -> None:
        seconds = self._frame_clock.restart() / 1000.0
        self._playback.advance(seconds)
        self._refresh()

    # --- sincronização da tela com o estado ---

    def _refresh(self) -> None:
        if self._toolpath is None:
            return

        pb = self._playback
        snapshot = self._toolpath.snapshot(pb.elapsed)
        self._viewport.render(snapshot)
        self._player.set_progress(pb.progress)
        self._player.set_playing(pb.playing)
        self._player.set_status(self._status_text(snapshot))
        self._sync_timer()

    def _sync_timer(self) -> None:
        if self._playback.playing and not self._timer.isActive():
            self._frame_clock.start()
            self._timer.start()
        elif not self._playback.playing and self._timer.isActive():
            self._timer.stop()

    def _status_text(self, snapshot: Snapshot) -> str:
        pb = self._playback
        text = (
            f"movimento {snapshot.done}/{self._toolpath.count}   |   "
            f"tempo {format_time(pb.elapsed)} / {format_time(pb.total_time)}   |   "
            f"velocidade {pb.speed:.1f}x"
        )
        if self._warnings:
            text += f"   |   {len(self._warnings)} aviso(s)"
        return text