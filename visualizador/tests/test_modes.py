import pytest

from core.dialect import get_dialect
from core.lexer import ERROR, WARNING
from core.modes import create_mode
from core.modes.base import apply_mode
from core.modes.deposition import BeadSpec, DepositionMode
from core.modes.machining import MachiningMode
from core.parser import parse_gcode
from core.toolpath import Toolpath

BEAD = BeadSpec(width=5.0, height=2.0, density=7.85)
ARC = get_dialect("arco-m8-m9")
GENERIC = get_dialect("generico")


def applied(text, mode, dialect=ARC):
    result = parse_gcode(text, dialect=dialect)
    return apply_mode(result.moves, mode)


def test_machining_work_is_cut_not_rapid_nor_dwell():
    moves = applied("G0 Z5\nG1 X10 F300\nG04 P1", MachiningMode(), dialect=GENERIC)
    assert [m.is_cut for m in moves] == [False, True, False]


def test_deposition_work_requires_process_on():
    text = "G1 X10 F300\nM8\nG04 P2\nM9\nG1 X20 F300"
    moves = applied(text, DepositionMode(BEAD))
    assert [m.is_cut for m in moves] == [False, True, False]


def test_travel_keeps_programmed_feed_when_not_work():
    moves = applied("G1 X60 F600", DepositionMode(BEAD))
    assert Toolpath(moves).durations[0] == pytest.approx(6.0)


def test_g0_with_process_on_is_error_on_its_line():
    mode = DepositionMode(BEAD)
    issues = mode.validate(applied("M8\nG0 X10\nM9", mode))
    assert any(i.severity == ERROR and i.line == 2 for i in issues)


def test_layer_step_different_from_bead_height_warns():
    mode = DepositionMode(BEAD)  # cordão de 2 mm
    issues = mode.validate(applied("M8\nG04 P1\nG91\nG1 Z5 F100\nG04 P1\nM9", mode))
    assert any(i.severity == WARNING and "passo entre camadas" in i.message for i in issues)


def test_deposited_volume_and_mass_from_bead():
    mode = DepositionMode(BEAD)
    toolpath = Toolpath(applied("M8\nG1 X100 F600\nM9", mode))
    cards = mode.cards(toolpath)
    # 100 mm × 5 mm × 2 mm = 1000 mm³ = 1 cm³; 1 cm³ de aço (7,85 g/cm³) = 0,00785 kg
    assert cards[0].detail.startswith("1.0 cm³")
    assert cards[0].value == "0.008 kg"


def test_machining_average_feed_card():
    moves = applied("G1 X60 F600", MachiningMode(), dialect=GENERIC)
    card = MachiningMode().cards(Toolpath(moves))[0]
    assert card.value == "600 mm/min"


def test_machining_cut_without_spindle_warns_once():
    moves = applied("G1 X10 F100\nG1 X20 F100", MachiningMode(), dialect=GENERIC)
    issues = MachiningMode().validate(moves)
    assert len(issues) == 1
    assert issues[0].line == 1


def test_create_mode_returns_matching_class():
    assert isinstance(create_mode("deposicao", BEAD), DepositionMode)
    assert isinstance(create_mode("usinagem", BEAD), MachiningMode)


def test_deposition_without_any_process_on_warns():
    mode = DepositionMode(BEAD)
    issues = mode.validate(applied("G1 X10 F100", mode))
    assert any("nenhum depósito encontrado" in i.message for i in issues)