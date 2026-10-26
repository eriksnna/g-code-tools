"""Modos de processo disponíveis e fábrica para criá-los."""
from __future__ import annotations

from core.modes.base import ModeCard, ProcessMode, apply_mode
from core.modes.deposition import BeadSpec, DepositionMode
from core.modes.machining import MachiningMode

MODE_CHOICES = [
    (MachiningMode.name, MachiningMode.key),
    (DepositionMode.name, DepositionMode.key),
]


def create_mode(key: str, bead: BeadSpec) -> ProcessMode:
    if key == MachiningMode.key:
        return MachiningMode()
    if key == DepositionMode.key:
        return DepositionMode(bead)
    raise ValueError(f"modo desconhecido: {key!r}")


__all__ = ["BeadSpec", "MODE_CHOICES", "ModeCard", "ProcessMode", "apply_mode", "create_mode"]