"""Modo de usinagem: trabalho é o corte com a ferramenta, com processo (spindle) ligado."""
from __future__ import annotations

import numpy as np

from core.lexer import WARNING, Issue
from core.modes.base import ModeCard, ProcessMode
from core.parser import Move
from core.toolpath import Toolpath


class MachiningMode(ProcessMode):
    key = "usinagem"
    name = "Usinagem"

    def is_work(self, move: Move) -> bool:
        return not move.rapid and move.dwell == 0

    def validate(self, moves: list[Move]) -> list[Issue]:
        # um único aviso basta: se o spindle nunca liga, todos os cortes seriam repetidos
        for move in moves:
            if move.is_cut and not move.active:
                return [Issue(move.line, WARNING,
                              "corte sem processo ligado (M3/M8 não ativado no dialeto?)")]
        return []

    def cards(self, toolpath: Toolpath) -> list[ModeCard]:
        cut = toolpath.is_cut
        cut_time = float(toolpath.durations[cut].sum())
        if cut_time <= 0:
            return []
        lengths = np.linalg.norm(toolpath.ends - toolpath.starts, axis=1)
        feed = float(lengths[cut].sum()) / cut_time * 60.0
        return [ModeCard("Avanço médio", f"{feed:.0f} mm/min", "trajeto de corte ÷ tempo de corte")]