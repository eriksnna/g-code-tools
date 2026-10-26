"""Contrato dos modos de processo: o que é trabalho e como validar."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace

from core.lexer import Issue
from core.parser import Move
from core.toolpath import Toolpath


@dataclass(frozen=True)
class ModeCard:
    """Cartão extra do painel de estatísticas, específico de um modo."""
    title: str
    value: str
    detail: str = ""


class ProcessMode(ABC):
    key: str
    name: str

    @abstractmethod
    def is_work(self, move: Move) -> bool:
        """True se o movimento produz trabalho (corte ou depósito)."""

    def validate(self, moves: list[Move]) -> list[Issue]:
        """Problemas específicos do modo. Recebe os movimentos já marcados por apply_mode."""
        return []

    def cards(self, toolpath: Toolpath) -> list[ModeCard]:
        return []


def apply_mode(moves: list[Move], mode: ProcessMode) -> list[Move]:
    """Marca em is_cut os movimentos de trabalho. O restante do pipeline não muda."""
    return [replace(move, is_cut=mode.is_work(move)) for move in moves]