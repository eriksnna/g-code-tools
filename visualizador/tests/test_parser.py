# tests/test_parser.py
import math

import pytest

from core.parser import ERROR, WARNING, arc_points, clean_line, parse_gcode

def test_clean_line_removes_comments_and_normalizes():
    assert clean_line("g1 x10 (lateral) ; fim") == "G1 X10"


def test_g1_after_g0_default_is_rapid_then_cut():
    result = parse_gcode("G1 X10 Y0 F300")
    move = result.moves[0]
    assert move.is_cut
    assert move.start == (0, 0, 0)
    assert move.end == (10, 0, 0)


def test_g0_is_rapid():
    result = parse_gcode("G0 X10")
    assert not result.moves[0].is_cut


def test_incremental_mode_accumulates_position():
    result = parse_gcode("G91\nG1 X5\nG1 X5")
    assert result.moves[-1].end == (10, 0, 0)


def test_inches_are_converted_to_mm_including_feed():
    result = parse_gcode("G20 G1 X1 F10")
    move = result.moves[0]
    assert move.end[0] == pytest.approx(25.4)
    assert move.feed == pytest.approx(254.0)


def test_zero_length_move_is_ignored():
    assert parse_gcode("G1 X0 Y0").moves == []


def test_arc_ends_exactly_at_target_and_keeps_radius():
    result = parse_gcode("G1 X50\nG3 X0 Y50 I-50 J0")
    arc_moves = result.moves[1:]
    assert arc_moves[-1].end == (0.0, 50.0, 0.0)
    for move in arc_moves:
        assert math.hypot(move.end[0], move.end[1]) == pytest.approx(50.0)


def test_cw_and_ccw_take_opposite_directions():
    ccw = arc_points((50, 0, 0), (0, 50, 0), (0, 0), clockwise=False)
    cw = arc_points((50, 0, 0), (0, 50, 0), (0, 0), clockwise=True)
    assert ccw[len(ccw) // 2][1] > 0    # G3 passa pelo primeiro quadrante
    assert cw[len(cw) // 2][1] < 0      # G2 dá a volta pelo terceiro quadrante


def test_arc_with_r_is_reported_as_error_with_line_number():
    result = parse_gcode("G1 X10\nG2 X0 Y10 R5")
    assert len(result.moves) == 1
    issue = result.issues[0]
    assert issue.line == 2
    assert issue.severity == ERROR

def test_multiple_g_codes_on_same_line_are_all_applied():
    result = parse_gcode("G91 G1 X5")
    assert result.moves[0].end == (5, 0, 0)

def test_missing_feed_warns_once_at_first_cut():
    result = parse_gcode("G1 X10\nG1 X20")
    feed_issues = [i for i in result.issues if "F ausente" in i.message]
    assert len(feed_issues) == 1
    assert feed_issues[0].line == 1
    assert feed_issues[0].severity == WARNING


def test_rapid_without_feed_does_not_warn():
    assert parse_gcode("G0 X10").issues == []


def test_move_outside_work_area_is_reported_once_per_line():
    limits = {"X": (0, 300), "Y": (0, 200), "Z": (-100, 100)}
    result = parse_gcode("G1 X400 Y400 F100", limits=limits)
    bounds = [i for i in result.issues if "área de trabalho" in i.message]
    assert len(bounds) == 1
    assert bounds[0].line == 1
    assert bounds[0].severity == ERROR


def test_moves_have_their_source_line():
    result = parse_gcode("G21\n\nG1 X10 F100\nG1 X20 F100")
    assert [m.line for m in result.moves] == [3, 4]