import pytest

from core.dialect import Dialect, get_dialect
from core.parser import parse_gcode
from core.stats import compute_stats
from core.toolpath import Toolpath

ARC_SECONDS = Dialect("teste", dwell_unit=1.0,
                      process_on=frozenset({8}), process_off=frozenset({9}))
ARC_MILLISECONDS = Dialect("teste ms", dwell_unit=0.001,
                           process_on=frozenset({8}), process_off=frozenset({9}))


def test_g04_is_a_timed_event_without_moving():
    result = parse_gcode("G1 X10 F600\nG04 P5", dialect=ARC_SECONDS)
    dwell = result.moves[-1]
    assert dwell.dwell == pytest.approx(5.0)
    assert dwell.start == dwell.end
    assert result.commands["G4"] == 1


def test_dwell_unit_follows_dialect():
    result = parse_gcode("G04 P5000", dialect=ARC_MILLISECONDS)
    assert result.moves[0].dwell == pytest.approx(5.0)


def test_process_flag_follows_dialect_m_codes():
    text = "G1 X1 F100\nM8\nG1 X2 F100\nM9\nG1 X3 F100"
    moves = parse_gcode(text, dialect=ARC_SECONDS).moves
    assert [m.active for m in moves] == [False, True, False]


def test_m_codes_outside_dialect_are_ignored():
    moves = parse_gcode("M8\nG1 X1 F100", dialect=get_dialect("generico")).moves
    assert moves[0].active is False


def test_rapid_flag_marks_g0_moves():
    moves = parse_gcode("G0 X10\nG1 X20 F100", dialect=get_dialect("generico")).moves
    assert [m.rapid for m in moves] == [True, False]


def test_g04_with_zero_or_missing_p_is_ignored():
    assert parse_gcode("G04 P0").moves == []
    assert parse_gcode("G04").moves == []