"""Constantes de configuração. Ajustes de máquina e de aparência ficam aqui."""
from pathlib import Path

APP_TITLE = "Visualizador de G-Code 3D"
WINDOW_SIZE = (1100, 800)
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICON_PATH = ASSETS_DIR / "g-code.ico"
GCODE_FILTER = "G-code (*.nc *.gcode *.ngc *.tap);;Todos os arquivos (*)"

# Máquina e interpretação
RAPID_FEED = 5000.0       # mm/min nos G0
DEFAULT_FEED = 300.0      # mm/min usado antes de qualquer F no arquivo
MIN_FEED = 1.0            # piso para evitar divisão por zero
INCH_TO_MM = 25.4
ARC_STEP_DEG = 5.0        # resolução dos arcos, em graus por segmento

# Visual
CUT_WIDTH = 2.0
RAPID_WIDTH = 1.0
HEAD_SIZE = 12
CAMERA_START_DISTANCE = 200.0
CAMERA_MARGIN = 1.5
CAMERA_MIN_DISTANCE = 50.0

# Reprodução
TICK_MS = 30
DEFAULT_SPEED = 1.0
SPEED_MIN = 0.1
SPEED_MAX = 10.0
SPEED_PRESETS = (0.5, 1.0, 1.5, 2.0, 4.0)
SPEED_SLIDER_SCALE = 10   # o slider trabalha em décimos
SEEK_STEP_FRACTION = 0.05
TIMELINE_STEPS = 1000

# Camadas: casas decimais usadas para agrupar profundidades iguais
LAYER_DECIMALS = 3

# Expansão de sub-rotinas
MAX_CALL_DEPTH = 10            # níveis de M98 aninhados antes de considerar recursão
MAX_EXPANDED_LINES = 100_000   # limite de segurança para o programa expandido

# Dialeto padrão de G-code (chave em core/dialect.py). Troque para o perfil da sua máquina.
DEFAULT_DIALECT = "generico"

# Modos de processo
DEFAULT_MODE = "usinagem"          # "usinagem" ou "deposicao"
BEAD_WIDTH_MM = 6.0                # largura do cordão (padrão, editável na interface)
BEAD_HEIGHT_MM = 3.0               # altura do cordão por camada
DEPOSIT_DENSITY_G_CM3 = 7.85       # aço carbono; ajuste para o seu arame

# Zoom do viewport 3D
ZOOM_STEP = 0.88          # fator multiplicativo por "clique" da roda (menor = zoom mais rápido)
ZOOM_MIN_DISTANCE = 5.0   # mm, não deixa a câmera colar na peça

# Visual da tocha (modo deposição)
TORCH_HEIGHT = 8.0      # mm, comprimento do corpo da tocha desenhada
TORCH_RADIUS = 1.5      # mm, raio da base da tocha
WIRE_STICKOUT = 3.0      # mm, distância entre a ponta da tocha e a peça
WIRE_WIDTH_PX = 1         # espessura visual do fio, em pixels de tela

TORCH_MAX_TILT_DEG = 8.0   # inclinação sutil, só para indicar a direção

# Segurança: limites para evitar que um arquivo malicioso ou corrompido trave o app
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024   # 20 MB; G-code real raramente passa disso
MAX_LINE_LENGTH = 10_000                 # caracteres; uma linha absurda indica arquivo corrompido/hostil