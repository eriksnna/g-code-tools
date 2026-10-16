# tests/test_playback.py
import pytest

from core.playback import Playback


def test_advance_scales_by_speed():
    pb = Playback(total_time=10.0, speed=2.0)
    pb.play()
    pb.advance(0.5)
    assert pb.elapsed == pytest.approx(1.0)


def test_playback_stops_at_end():
    pb = Playback(total_time=10.0)
    pb.play()
    pb.advance(100.0)
    assert pb.elapsed == 10.0
    assert not pb.playing


def test_play_after_end_restarts_from_zero():
    pb = Playback(total_time=10.0)
    pb.seek(10.0)
    pb.play()
    assert pb.elapsed == 0.0
    assert pb.playing


def test_seek_is_clamped_to_range():
    pb = Playback(total_time=10.0)
    pb.seek(-5.0)
    assert pb.elapsed == 0.0
    pb.seek(99.0)
    assert pb.elapsed == 10.0


def test_step_pauses_and_stays_in_range():
    pb = Playback(total_time=100.0)
    pb.play()
    pb.step(-1)
    assert not pb.playing
    assert pb.elapsed == 0.0


def test_speed_is_rounded_and_clamped():
    pb = Playback(total_time=10.0)
    pb.set_speed(0.01)
    assert pb.speed == 0.1
    pb.set_speed(50.0)
    assert pb.speed == 10.0