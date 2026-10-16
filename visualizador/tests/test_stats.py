import pytest

from core.parser import Move
from core.stats import compute_stats, format_duration, format_length
from core.toolpath import Toolpath


def make_path():
    # duas camadas de corte (z=0 e z=-5); um rápido de volta
    return Toolpath(
        [
            Move((0, 0, 0), (10, 0, 0), is_cut=True, feed=600.0),       # 1 s, 10 mm
            Move((10, 0, 0), (10, 0, -5), is_cut=True, feed=600.0),     # 0,5 s, 5 mm
            Move((10, 0, -5), (0, 0, -5), is_cut=True, feed=600.0),     # 1 s, 10 mm
            Move((0, 0, -5), (0, 0, 0), is_cut=False, feed=0.0),        # 1 s, 5 mm
        ],
        rapid_feed=300.0,
    )


def test_counts_split_by_move_type():
    stats = compute_stats(make_path())
    assert stats.total_moves == 4
    assert stats.cut_moves == 3
    assert stats.rapid_moves == 1


def test_times_split_by_move_type():
    stats = compute_stats(make_path())
    assert stats.cut_time == pytest.approx(2.5)
    assert stats.rapid_time == pytest.approx(1.0)
    assert stats.total_time == pytest.approx(3.5)


def test_lengths_split_by_move_type():
    stats = compute_stats(make_path())
    assert stats.cut_length == pytest.approx(25.0)
    assert stats.rapid_length == pytest.approx(5.0)


def test_layers_count_distinct_cut_depths():
    assert compute_stats(make_path()).layer_count == 2


def test_size_ignores_rapid_moves():
    path = Toolpath(
        [
            Move((0, 0, 0), (10, 10, 0), is_cut=True, feed=600.0),
            Move((10, 10, 0), (500, 500, 0), is_cut=False, feed=0.0),
        ],
        rapid_feed=5000.0,
    )
    assert compute_stats(path).size == pytest.approx((10.0, 10.0, 0.0))


def test_format_duration():
    assert format_duration(0) == "00:00"
    assert format_duration(59.6) == "01:00"
    assert format_duration(3725) == "1:02:05"


def test_format_length():
    assert format_length(12.345) == "12.3 mm"

def test_commands_are_counted_per_line_not_per_segment():
    from core.parser import parse_gcode

    result = parse_gcode("G0 Z5\nG1 Z-1 F100\nG2 X10 Y0 I5 J0 F100")
    stats = compute_stats(Toolpath(result.moves), result.commands)

    assert result.commands == {"G0": 1, "G1": 1, "G2": 1, "G3": 0}
    assert stats.commands == result.commands
    assert stats.total_moves > 3  # o arco vira vários segmentos