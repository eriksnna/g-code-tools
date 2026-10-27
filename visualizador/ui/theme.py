"""Cores e folha de estilo. Trocar o visual é feito apenas aqui."""

BACKGROUND = "#16181d"
GRID_COLOR = (70, 75, 85, 255)

# Cores do traçado em OpenGL (RGBA, de 0 a 1)
DIM_CUT = (0.2, 0.5, 0.7, 0.35)
BRIGHT_CUT = (0.2, 0.8, 1.0, 1.0)
DIM_RAPID = (1.0, 0.35, 0.35, 0.2)
BRIGHT_RAPID = (1.0, 0.35, 0.35, 0.8)
HEAD_COLOR = (1.0, 0.85, 0.2, 1.0)
ARC_HEAD_COLOR = (1.0, 0.45, 0.1, 1.0)  # cabeça com processo ligado
ERROR_COLOR = "#ff6b6b"
WARNING_COLOR = "#f0b429"
CUT_DEPTH_ALPHA = 0.35  # opacidade dos cortes apagados na coloração por profundidade
DEPTH_STOPS = (         # do mais fundo ao topo
    (0.25, 0.5, 1.0),
    (0.3, 0.9, 0.7),
    (1.0, 0.85, 0.2),
)

DARK_QSS = """
QMainWindow { background: #16181d; }
QWidget#central { background: #16181d; }
QLabel { color: #e6e6e6; background: transparent; font-size: 13px; }
QLabel#fileLabel { color: #8b94a5; }
QLabel#status { color: #9aa3b2; font-family: Consolas, monospace; font-size: 12px; }
QPushButton {
    background: #2a2e38; color: #e6e6e6;
    border: 1px solid #3a3f4b; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background: #343945; }
QPushButton:pressed { background: #1f222a; }
QPushButton:disabled { color: #5a606d; }
QPushButton#play { background: #2b6cb0; border: 1px solid #3b82d0; font-size: 16px; }
QPushButton#play:hover { background: #3478c4; }
QPushButton#preset { padding: 2px 4px; font-size: 12px; }
QPushButton#preset:checked { background: #3b82d0; border: 1px solid #3b82d0; }
QFrame#playbar {
    background: #1f222a; border: 1px solid #2c303b; border-radius: 10px;
}
QSlider::groove:horizontal { height: 6px; background: #343945; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #3b82d0; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #e6e6e6; width: 14px; margin: -5px 0; border-radius: 7px;
}
QSlider:disabled::handle:horizontal { background: #5a606d; }
QFrame#statsPanel {
    background: #1f222a; border: 1px solid #2c303b; border-radius: 10px;
}
QFrame#card {
    background: #272b35; border: 1px solid #323744; border-radius: 8px;
}
QLabel#cardTitle { color: #7d8698; font-size: 10px; font-weight: bold; }
QLabel#cardValue { color: #f0f2f5; font-size: 16px; font-weight: 600; }
QLabel#sectionTitle {
    color: #9aa3b2; font-size: 11px; font-weight: bold; margin-top: 4px;
}
QProgressBar { background: #343945; border: none; border-radius: 4px; }
QProgressBar::chunk { background: #3b82d0; border-radius: 4px; }
QListWidget#warnings {
    background: #272b35; color: #f0b429;
    border: 1px solid #323744; border-radius: 8px; font-size: 12px;
}
QComboBox {
    background: #2a2e38; color: #e6e6e6;
    border: 1px solid #3a3f4b; border-radius: 6px; padding: 4px 8px; min-width: 120px;
}
QComboBox QAbstractItemView {
    background: #2a2e38; color: #e6e6e6; selection-background-color: #3b82d0;
}
QCheckBox { color: #e6e6e6; spacing: 6px; }
QFrame#issuesPanel {
    background: #1f222a; border: 1px solid #2c303b; border-radius: 10px;
}
QLabel#issueSummary { color: #9aa3b2; font-size: 12px; }
QLabel#issueEmpty { color: #6fcf97; font-size: 12px; }
QLabel#issueDetail {
    color: #9aa3b2; font-family: Consolas, monospace; font-size: 11px;
    background: #272b35; border-radius: 6px; padding: 6px;
}
QListWidget#issues {
    background: #272b35; border: 1px solid #323744; border-radius: 8px; font-size: 12px;
}
QListWidget#issues::item { padding: 4px; }
QListWidget#issues::item:selected { background: #343945; }

QFrame#editorPanel {
    background: #1f222a; border: 1px solid #2c303b; border-radius: 10px;
}
QPlainTextEdit#codeEditor {
    background: #14161b; color: #d7dce3;
    border: 1px solid #2c303b; border-radius: 6px;
    selection-background-color: #3b82d0;
}
QLabel#editorStatus { color: #f0b429; font-size: 11px; font-weight: bold; }
QPushButton#applyEdit { background: #2b6cb0; border: 1px solid #3b82d0; }
QPushButton#applyEdit:hover { background: #3478c4; }
QPushButton#editorToggle:checked { background: #3b82d0; border: 1px solid #3b82d0; }
"""