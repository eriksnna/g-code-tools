"""Estado de reprodução: tempo, velocidade e play/pause. Não depende de Qt."""
from __future__ import annotations

from config import DEFAULT_SPEED, SEEK_STEP_FRACTION, SPEED_MAX, SPEED_MIN


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class Playback:
    def __init__(self, total_time: float = 0.0, speed: float = DEFAULT_SPEED) -> None:
        self.total_time = total_time
        self.speed = speed
        self.elapsed = 0.0
        self.playing = False

    @property
    def progress(self) -> float:
        return self.elapsed / self.total_time if self.total_time > 0 else 0.0

    @property
    def finished(self) -> bool:
        return self.elapsed >= self.total_time

    def reset(self, total_time: float) -> None:
        """Prepara a reprodução para um novo caminho. A velocidade é mantida."""
        self.total_time = total_time
        self.elapsed = 0.0
        self.playing = False

    def play(self) -> None:
        if self.finished:
            self.elapsed = 0.0
        self.playing = True

    def pause(self) -> None:
        self.playing = False

    def toggle(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    def advance(self, real_seconds: float) -> None:
        """Avança o relógio simulado de acordo com o tempo real decorrido."""
        if not self.playing:
            return
        self.seek(self.elapsed + real_seconds * self.speed)
        if self.finished:
            self.pause()

    def seek(self, seconds: float) -> None:
        self.elapsed = clamp(seconds, 0.0, self.total_time)

    def seek_fraction(self, fraction: float) -> None:
        self.seek(clamp(fraction, 0.0, 1.0) * self.total_time)

    def step(self, direction: int) -> None:
        self.pause()
        self.seek(self.elapsed + direction * SEEK_STEP_FRACTION * self.total_time)

    def set_speed(self, value: float) -> None:
        self.speed = clamp(round(value, 1), SPEED_MIN, SPEED_MAX)