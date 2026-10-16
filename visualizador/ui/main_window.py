"""Janela principal: liga a interface ao modelo e ao estado de reprodução."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QVBoxLayout, QWidget,
)

from config import APP_TITLE, GCODE_FILTER, ICON_PATH, TICK_MS, WINDOW_SIZE
from core.layers import depth_levels
from core.parser import ERROR, Issue, parse_gcode
from core.playback import Playback
from core.stats import compute_stats, format_duration
from core.toolpath import Snapshot, Toolpath
from ui.issues_panel import IssuesPanel
from ui.layer_controls import LayerControls
from ui.player_bar import PlayerBar
from ui.stats_panel import StatsPanel
from ui.theme import DARK_QSS
from ui.viewport import ToolpathView


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(*WINDOW_SIZE)
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setStyleSheet(DARK_QSS)

        self._toolpath: Toolpath | None = None
        self._issues: list[Issue] = []
        self._source_lines: list[str] = []
        self._playback = Playback()

        self._open_button = QPushButton("Abrir G-code...")
        self._file_label = QLabel("Nenhum arquivo carregado")
        self._file_label.setObjectName("fileLabel")
        self._layer_controls = LayerControls()
        self._viewport = ToolpathView()
        self._stats_panel = StatsPanel()
        self._issues_panel = IssuesPanel()
        self._player = PlayerBar()

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._on_tick)
        self._frame_clock = QElapsedTimer()

        self._build_layout()
        self._connect_signals()
        self._player.set_speed(self._playback.speed)
        self._player.set_enabled(False)
        self._layer_controls.set_levels([])

    # --- montagem ---

    def _build_layout(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(self._open_button)
        header.addWidget(self._file_label, 1)
        header.addWidget(self._layer_controls)

        side = QVBoxLayout()
        side.setSpacing(10)
        side.addWidget(self._stats_panel)
        side.addWidget(self._issues_panel, 1)

        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self._viewport, 1)
        body.addLayout(side)

        root.addLayout(header)
        root.addLayout(body, 1)
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

        c = self._layer_controls
        c.filter_changed.connect(self._viewport.set_layer_filter)
        c.depth_coloring_toggled.connect(self._viewport.set_depth_coloring)

        self._issues_panel.issue_selected.connect(self._go_to_issue)

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
        self._source_lines = text.splitlines()
        self._issues = result.issues
        self._issues_panel.show_issues(result.issues)

        if not result.moves:
            self._show_empty()
            return

        toolpath = Toolpath(result.moves)
        levels = depth_levels(toolpath)
        self._toolpath = toolpath
        self._layer_controls.set_levels(levels)
        self._playback.reset(toolpath.total_time)
        self._viewport.show_toolpath(toolpath, levels)
        self._stats_panel.show_program(compute_stats(toolpath))
        self._player.set_enabled(True)
        self._refresh()

    def _show_empty(self) -> None:
        self._toolpath = None
        self._viewport.clear()
        self._stats_panel.clear()
        self._layer_controls.set_levels([])
        self._player.set_enabled(False)
        self._player.set_status("Nenhum movimento encontrado no arquivo.")

    # --- validação ---

    def _go_to_issue(self, line: int) -> None:
        if 1 <= line <= len(self._source_lines):
            self._issues_panel.show_source(line, self._source_lines[line - 1].strip())

        if self._toolpath is None:
            return
        t = self._toolpath.time_at_line(line)
        if t is None:
            self._player.set_status(f"Nenhum movimento a partir da linha {line}.")
            return

        self._playback.pause()
        self._playback.seek(t)
        self._refresh()

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
        self._stats_panel.show_progress(
            pb.elapsed, pb.total_time, snapshot.done, self._toolpath.count,
        )
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
            f"tempo {format_duration(pb.elapsed)} / {format_duration(pb.total_time)}   |   "
            f"velocidade {pb.speed:.1f}x"
        )
        if self._issues:
            text += f"   |   {len(self._issues)} problema(s)"
        return text