"""Janela principal: liga a interface ao modo de processo, ao modelo e à reprodução."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QElapsedTimer, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QSplitter, QVBoxLayout, QWidget, QMessageBox, QStackedWidget,
)

from config import APP_TITLE, GCODE_FILTER, ICON_PATH, TICK_MS, WINDOW_SIZE
from core.layers import depth_levels
from core.lexer import Issue
from core.modes import apply_mode
from core.parser import parse_gcode
from core.playback import Playback
from core.stats import compute_stats, format_duration
from core.toolpath import Snapshot, Toolpath
from ui.dialect_controls import DialectControls
from ui.gcode_editor import GCodeEditor
from ui.issues_panel import IssuesPanel
from ui.layer_controls import LayerControls
from ui.mode_controls import ModeControls
from ui.player_bar import PlayerBar
from ui.stats_panel import StatsPanel
from ui.theme import DARK_QSS
from ui.viewport import ToolpathView
from ui.start_panel import StartPanel


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(*WINDOW_SIZE)
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setStyleSheet(DARK_QSS)

        self._path: Path | None = None
        self._text: str | None = None
        self._toolpath: Toolpath | None = None
        self._issues: list[Issue] = []
        self._source_lines: list[str] = []
        self._playback = Playback()

        self._open_button = QPushButton("Abrir G-code...")
        self._file_label = QLabel("Nenhum arquivo carregado")
        self._file_label.setObjectName("fileLabel")
        self._mode_controls = ModeControls()
        self._dialect_controls = DialectControls()
        self._editor_toggle = QPushButton("Editor")
        self._editor_toggle.setObjectName("editorToggle")
        self._editor_toggle.setCheckable(True)
        self._layer_controls = LayerControls()
        self._viewport = ToolpathView()
        self._editor = GCodeEditor()
        self._editor.setVisible(False)
        self._stats_panel = StatsPanel()
        self._issues_panel = IssuesPanel()
        self._player = PlayerBar()

        self._start_panel = StartPanel()
        self._stack = QStackedWidget()

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
        header.addWidget(self._mode_controls)
        header.addWidget(self._dialect_controls)
        header.addWidget(self._editor_toggle)
        header.addWidget(self._layer_controls)

        stats_scroll = QScrollArea()
        stats_scroll.setWidgetResizable(True)
        stats_scroll.setFrameShape(QFrame.Shape.NoFrame)
        stats_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        stats_scroll.setWidget(self._stats_panel)

        side = QSplitter(Qt.Orientation.Vertical)
        side.addWidget(stats_scroll)
        side.addWidget(self._issues_panel)
        side.setStretchFactor(0, 1)
        side.setStretchFactor(1, 1)
        side.setChildrenCollapsible(False)

        self._viewport.setMinimumSize(400, 200)
        main_area = QSplitter(Qt.Orientation.Vertical)
        main_area.addWidget(self._viewport)
        main_area.addWidget(self._editor)
        main_area.setStretchFactor(0, 1)
        main_area.setStretchFactor(1, 0)
        main_area.setChildrenCollapsible(True)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(main_area)
        body.addWidget(side)
        body.setStretchFactor(0, 1)
        body.setSizes([760, 320])
        body.setChildrenCollapsible(False)

        self._stack.addWidget(self._start_panel)
        self._stack.addWidget(body)
        self._stack.setCurrentWidget(self._start_panel)

        self._header_widget = QWidget()
        self._header_widget.setLayout(header)
        self._header_widget.setVisible(False)
        self._player.setVisible(False)

        root.addWidget(self._header_widget)
        root.addWidget(self._stack, 1)
        root.addWidget(self._player)
        self.setCentralWidget(central)

    def _enter_workspace(self) -> None:
        """Sai da tela inicial: mostra cabeçalho, área de trabalho e barra de reprodução."""
        self._header_widget.setVisible(True)
        self._player.setVisible(True)
        self._stack.setCurrentIndex(1)

    def _connect_signals(self) -> None:
        self._open_button.clicked.connect(lambda _checked=False: self.open_file())
        self._mode_controls.changed.connect(self._reload)
        self._dialect_controls.changed.connect(self._reload)
        self._editor_toggle.toggled.connect(self._editor.setVisible)
        self._editor.apply_requested.connect(lambda _text: self._editor_toggle.setChecked(True))
        self._editor.save_requested.connect(self._save_edited_text)
        self._editor.save_as_requested.connect(self._save_edited_text_as)
        self._editor.apply_requested.connect(self._apply_edited_text)

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
        self._issues_panel.issue_selected.connect(self._editor.goto_line)

        self._start_panel.open_requested.connect(lambda: self.open_file())
        self._start_panel.blank_requested.connect(self._start_blank)

    # --- carregamento ---

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Abrir G-code", "", GCODE_FILTER)
        if path:
            self.load_file(Path(path))

    def _start_blank(self) -> None:
        """Começa um programa vazio direto no editor, sem arquivo de origem."""
        self._path = None
        self._text = ""
        self._file_label.setText("Novo programa (não salvo)")
        self._editor.set_text("")
        self._editor_toggle.setChecked(True)
        self._enter_workspace()
        self._show_empty()

    def load_file(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as err:
            self._player.set_status(f"Erro ao abrir arquivo: {err}")
            return
        self._path = path
        self._text = text
        self._file_label.setText(str(path))
        self._editor.set_text(text)
        self._enter_workspace()
        self._reload()

    def _apply_edited_text(self, text: str) -> None:
        """O usuário editou o G-code no painel e pediu para reinterpretar."""
        self._text = text
        self._editor.mark_applied()
        self._reload()

    def _save_edited_text(self, text: str) -> None:
        """Salva no arquivo aberto; sem arquivo de origem, pede um caminho novo."""
        if self._path is None:
            self._save_edited_text_as(text)
            return
        self._write_to_path(self._path, text)

    def _save_edited_text_as(self, text: str) -> None:
        """Sempre pergunta o caminho, mesmo que já exista um arquivo aberto."""
        path_str, _ = QFileDialog.getSaveFileName(self, "Salvar G-code como", "", GCODE_FILTER)
        if not path_str:
            return
        path = Path(path_str)
        if self._write_to_path(path, text):
            self._path = path
            self._file_label.setText(str(path))

    def _write_to_path(self, path: Path, text: str) -> bool:
        try:
            path.write_text(text, encoding="utf-8")
        except OSError as err:
            QMessageBox.warning(self, "Erro ao salvar", f"Não foi possível salvar: {err}")
            return False
        self._apply_edited_text(text)
        self._player.set_status(f"Salvo em {path}")
        return True

    def _reload(self) -> None:
        """Reinterpreta o texto atual com o modo e o dialeto escolhidos."""
        if self._text is None:
            return
        self._pause()

        mode = self._mode_controls.current_mode()
        dialect = self._dialect_controls.current_dialect()
        result = parse_gcode(self._text, dialect=dialect)
        moves = apply_mode(result.moves, mode)

        self._source_lines = self._text.splitlines()
        self._issues = sorted([*result.issues, *mode.validate(moves)], key=lambda i: i.line)
        self._issues_panel.show_issues(self._issues)
        self._layer_controls.setVisible(mode.key != "deposicao")

        if not moves:
            self._show_empty()
            return

        toolpath = Toolpath(moves)
        levels = depth_levels(toolpath)
        self._toolpath = toolpath
        self._layer_controls.set_levels(levels)
        self._playback.reset(toolpath.total_time)
        self._viewport.show_toolpath(toolpath, levels)
        self._viewport.set_show_torch(mode.key == "deposicao")
        self._stats_panel.show_program(compute_stats(toolpath, result.commands))
        self._stats_panel.show_mode(mode.name, mode.cards(toolpath))
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
        self._editor_toggle.setChecked(True)
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
        if snapshot.active:
            text += "   |   processo ativo"
        if self._issues:
            text += f"   |   {len(self._issues)} problema(s)"
        return text