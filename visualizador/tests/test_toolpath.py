# tests/test_toolpath.py
import pytest

from core.parser import Move
from core.toolpath import Toolpath


def make_path():
    return Toolpath(
        [
            Move((0, 0, 0), (60, 0, 0), is_cut=True, feed=600.0),      # 6 s
            Move((60, 0, 0), (0, 0, 0), is_cut=False, feed=0.0),       # 0,6 s com 6000 mm/min
        ],
        rapid_feed=6000.0,
    )


def test_durations_use_cut_feed_and_rapid_feed():
    path = make_path()
    assert path.durations == pytest.approx([6.0, 0.6])
    assert path.total_time == pytest.approx(6.6)


def test_snapshot_interpolates_inside_a_move():
    snap = make_path().snapshot(3.0)
    assert snap.head[0] == pytest.approx(30.0)
    assert snap.done == 0
    assert snap.started == 1

def test_time_at_line_returns_start_of_first_move_from_that_line():
    path = Toolpath([
        Move((0, 0, 0), (10, 0, 0), is_cut=True, feed=600.0, line=1),  # 1 s
        Move((10, 0, 0), (20, 0, 0), is_cut=True, feed=600.0, line=3),  # começa em 1 s
    ])
    assert path.time_at_line(2) == pytest.approx(1.0)
    assert path.time_at_line(4) is None