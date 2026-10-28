"""Perfis de máquina: limites de curso, modo de processo e dialeto por máquina.

Reúne tudo que descreve uma configuração completa de máquina/processo: limites de
curso (segurança/área de trabalho), modo de processo padrão (usinagem ou deposição)
e dialeto de G-code (como interpretar M-codes).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from config import DEFAULT_DIALECT, DEFAULT_MODE

Limits = dict[str, tuple[float, float]]

DEFAULT_LIMITS: Limits = {"X": (0.0, 300.0), "Y": (0.0, 200.0), "Z": (-100.0, 100.0)}


@dataclass
class MachineProfile:
    name: str
    limits: Limits = field(default_factory=lambda: dict(DEFAULT_LIMITS))
    mode_key: str = DEFAULT_MODE
    dialect_key: str = DEFAULT_DIALECT

    def clone(self) -> "MachineProfile":
        return MachineProfile(self.name, dict(self.limits), self.mode_key, self.dialect_key)


def default_profiles() -> list[MachineProfile]:
    """Perfis iniciais oferecidos na interface. O usuário pode editar qualquer campo."""
    return [
        MachineProfile("Minha máquina", dict(DEFAULT_LIMITS), DEFAULT_MODE, DEFAULT_DIALECT),
        MachineProfile(
            "Sem limite (ignorar área de trabalho)",
            {"X": (-1e9, 1e9), "Y": (-1e9, 1e9), "Z": (-1e9, 1e9)},
            DEFAULT_MODE,
            DEFAULT_DIALECT,
        ),
    ]