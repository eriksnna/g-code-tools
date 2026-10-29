"""Cores e folha de estilo. Trocar o visual é feito apenas aqui.

Paleta inspirada no modo escuro da Apple (macOS/iOS): camadas de cinza em vez
de bordas marcadas, azul vívido de destaque, cantos bem arredondados. Os
tokens abaixo (SURFACE_*, ACCENT, RADIUS_*) centralizam cor/forma — mude só
aqui pra afetar o app inteiro.
"""

# --- tokens de design ---------------------------------------------------

SURFACE_0 = "#0d0e12"   # fundo da janela
SURFACE_1 = "#17191f"   # painéis (cartões, barra de reprodução, editor...)
SURFACE_2 = "#1f222a"   # elementos dentro de painéis (inputs, itens de lista)
SURFACE_3 = "#282c36"   # hover / destaque leve
BORDER = "#2c303b"
BORDER_STRONG = "#3a3f4b"

TEXT_PRIMARY = "#f2f3f5"
TEXT_SECONDARY = "#9aa3b2"
TEXT_MUTED = "#5a606d"

ACCENT = "#c9622a"
ACCENT_HOVER = "#e0773a"
ACCENT_PRESSED = "#a84f1f"

SUCCESS = "#30d158"
ERROR_COLOR = "#ff6b6b"
WARNING_COLOR = "#f0b429"
ICON_COLOR = TEXT_PRIMARY

RADIUS_SM = "6px"
RADIUS_MD = "8px"
RADIUS_LG = "12px"

FONT_FAMILY = "'Segoe UI Variable Display', 'Segoe UI', sans-serif"

# --- cores usadas no viewport 3D (OpenGL, não QSS) -----------------------

BACKGROUND = SURFACE_0
GRID_COLOR = (70, 75, 85, 255)

DIM_CUT = (0.2, 0.5, 0.7, 0.35)
BRIGHT_CUT = (0.2, 0.8, 1.0, 1.0)
DIM_RAPID = (1.0, 0.35, 0.35, 0.2)
BRIGHT_RAPID = (1.0, 0.35, 0.35, 0.8)
HEAD_COLOR = (1.0, 0.85, 0.2, 1.0)
ARC_HEAD_COLOR = (1.0, 0.45, 0.1, 1.0)
TORCH_COLOR = (0.55, 0.57, 0.62, 1.0)
WIRE_COLOR = (0.95, 0.95, 0.95, 1.0)
CUT_DEPTH_ALPHA = 0.35
DEPTH_STOPS = (
    (0.25, 0.5, 1.0),
    (0.3, 0.9, 0.7),
    (1.0, 0.85, 0.2),
)

# --- folha de estilo ------------------------------------------------------

DARK_QSS = f"""
QMainWindow {{ background: {SURFACE_0}; }}
QWidget#central {{ background: {SURFACE_0}; }}
QDialog {{ background: {SURFACE_0}; }}
QDialog QLabel {{ color: {TEXT_PRIMARY}; }}

QLabel {{ color: {TEXT_PRIMARY}; background: transparent; font-family: {FONT_FAMILY}; font-size: 13px; }}
QLabel#fileLabel {{ color: {TEXT_SECONDARY}; }}
QLabel#profileLabel {{ color: {TEXT_SECONDARY}; font-weight: 600; }}
QLabel#status {{ color: {TEXT_SECONDARY}; font-family: Consolas, monospace; font-size: 12px; }}

QPushButton {{
    background: {SURFACE_2}; color: {TEXT_PRIMARY}; font-family: {FONT_FAMILY};
    border: none; border-radius: {RADIUS_MD}; padding: 7px 14px; font-weight: 500;
}}
QPushButton:hover {{ background: {SURFACE_3}; }}
QPushButton:pressed {{ background: {SURFACE_1}; }}
QPushButton:disabled {{ color: {TEXT_MUTED}; }}
QPushButton:focus {{ border: 1px solid {ACCENT}; }}

QPushButton#play {{
    background: {ACCENT}; border-radius: 24px; padding: 0; font-size: 16px;
}}
QPushButton#play:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#play:pressed {{ background: {ACCENT_PRESSED}; }}

QPushButton#transport {{ background: transparent; border-radius: 20px; padding: 0; }}
QPushButton#transport:hover {{ background: {SURFACE_3}; }}
QPushButton#transport:pressed {{ background: {SURFACE_1}; }}

QPushButton#preset {{ padding: 3px 10px; font-size: 12px; border-radius: {RADIUS_SM}; background: {SURFACE_2}; }}
QPushButton#preset:hover {{ background: {SURFACE_3}; }}
QPushButton#preset:checked {{ background: {ACCENT}; color: #ffffff; }}

QFrame#playbar {{ background: {SURFACE_1}; border: none; border-radius: {RADIUS_LG}; }}

QFrame#statsPanel {{ background: {SURFACE_1}; border: none; border-radius: {RADIUS_LG}; }}
QFrame#card {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: {RADIUS_MD}; }}
QLabel#cardTitle {{ color: {TEXT_SECONDARY}; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }}
QLabel#cardValue {{ color: {TEXT_PRIMARY}; font-size: 17px; font-weight: 700; }}
QLabel#sectionTitle {{ color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700; margin-top: 4px; }}

QProgressBar {{ background: {SURFACE_2}; border: none; border-radius: 4px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}

QListWidget {{
    background: {SURFACE_2}; color: {TEXT_PRIMARY};
    border: none; border-radius: {RADIUS_MD}; font-size: 12px;
}}
QListWidget::item {{ padding: 6px 10px; border-radius: 6px; }}
QListWidget::item:hover {{ background: {SURFACE_3}; }}
QListWidget::item:selected {{ background: {ACCENT}; color: #ffffff; }}
QListWidget#warnings {{ color: {WARNING_COLOR}; }}

QComboBox {{
    background: {SURFACE_2}; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_MD}; padding: 5px 10px; min-width: 120px;
}}
QComboBox:hover {{ border: 1px solid {TEXT_SECONDARY}; }}
QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER};
    border-radius: {RADIUS_SM}; selection-background-color: {ACCENT}; outline: none;
}}

QCheckBox {{ color: {TEXT_PRIMARY}; spacing: 8px; font-family: {FONT_FAMILY}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border-radius: 5px;
    border: 1px solid {BORDER_STRONG}; background: {SURFACE_2};
}}
QCheckBox::indicator:hover {{ border: 1px solid {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}

QLineEdit {{
    background: {SURFACE_2}; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_MD}; padding: 6px 10px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QLineEdit:disabled {{ color: {TEXT_MUTED}; }}

QDoubleSpinBox {{
    background: {SURFACE_2}; color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS_MD}; padding: 4px 8px;
}}
QDoubleSpinBox:focus {{ border: 1px solid {ACCENT}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ background: transparent; border: none; width: 18px; }}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{ background: {SURFACE_3}; }}

QGroupBox {{
    color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 700;
    border: 1px solid {BORDER}; border-radius: {RADIUS_LG};
    margin-top: 12px; padding-top: 16px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {TEXT_SECONDARY}; }}

QFrame#issuesPanel {{ background: {SURFACE_1}; border: none; border-radius: {RADIUS_LG}; }}
QLabel#issueSummary {{ color: {TEXT_SECONDARY}; font-size: 12px; }}
QLabel#issueEmpty {{ color: {SUCCESS}; font-size: 12px; }}
QLabel#issueDetail {{
    color: {TEXT_SECONDARY}; font-family: Consolas, monospace; font-size: 11px;
    background: {SURFACE_2}; border-radius: {RADIUS_SM}; padding: 6px;
}}

QFrame#editorPanel {{ background: {SURFACE_1}; border: none; border-radius: {RADIUS_LG}; }}
QPlainTextEdit#codeEditor {{
    background: {SURFACE_0}; color: #d7dce3;
    border: none; border-radius: {RADIUS_MD};
    selection-background-color: {ACCENT};
}}
QLabel#editorStatus {{ color: {WARNING_COLOR}; font-size: 11px; font-weight: 700; }}
QPushButton#applyEdit {{ background: {ACCENT}; }}
QPushButton#applyEdit:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#editorToggle:checked {{ background: {ACCENT}; }}
QPushButton#saveEdit {{ background: {SURFACE_2}; }}
QPushButton#saveAsEdit {{ background: {SURFACE_2}; }}
QPushButton#editorHelp {{ background: {SURFACE_2}; border-radius: 14px; font-weight: 700; }}
QWidget#findBar {{ background: {SURFACE_2}; border-radius: {RADIUS_MD}; }}
QLabel#findStatus {{ color: {WARNING_COLOR}; font-size: 11px; }}

QFrame#startPanel {{ background: {SURFACE_0}; }}
QLabel#startTitle {{ color: {TEXT_PRIMARY}; font-size: 24px; font-weight: 700; }}
QLabel#startSubtitle {{ color: {TEXT_SECONDARY}; font-size: 13px; }}
QPushButton#startButton {{
    background: {ACCENT}; padding: 12px 20px; font-size: 13px; font-weight: 600;
    border-radius: {RADIUS_MD};
}}
QPushButton#startButton:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#startButtonSecondary {{ padding: 12px 20px; font-size: 13px; border-radius: {RADIUS_MD}; }}

QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_STRONG}; border-radius: 5px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; background: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{
    background: transparent; height: 10px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_STRONG}; border-radius: 5px; min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {TEXT_MUTED}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; border: none; background: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
"""