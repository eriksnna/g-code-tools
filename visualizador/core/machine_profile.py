"""Perfis de máquina: limites de curso e outras configurações de segurança por máquina.

Diferente do Dialect (que decide como interpretar M-codes), o MachineProfile decide
o que é seguro ou permitido para uma máquina física específica.
"""
from __future__ import annotations

from dataclasses import dataclass, field

Limits = dict[str, tuple[float, float]]

DEFAULT_LIMITS: Limits = {"X": (0.0, 300.0), "Y": (0.0, 200.0), "Z": (-100.0, 100.0)}


@dataclass
class MachineProfile:
    name: str
    limits: Limits = field(default_factory=lambda: dict(DEFAULT_LIMITS))

    def clone(self) -> "MachineProfile":
        return MachineProfile(self.name, dict(self.limits))


def default_profiles() -> list[MachineProfile]:
    """Perfis iniciais oferecidos na interface. O usuário pode editar os limites de qualquer um."""
    return [
        MachineProfile("Minha máquina", dict(DEFAULT_LIMITS)),
        MachineProfile("Sem limite (ignorar área de trabalho)",
                       {"X": (-1e9, 1e9), "Y": (-1e9, 1e9), "Z": (-1e9, 1e9)}),
    ]