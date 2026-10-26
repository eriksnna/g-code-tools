"""Modo de deposição (WAAM): trabalho é o material depositado com o processo ligado."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from core.lexer import ERROR, WARNING, Issue
from core.modes.base import ModeCard, ProcessMode
from core.parser import Move
from core.stats import format_duration, format_length
from core.toolpath import Toolpath

HEIGHT_TOLERANCE = 0.2   # mm: diferença aceita entre o passo de camada e a altura do cordão
MM3_PER_CM3 = 1000.0


@dataclass(frozen=True)
class BeadSpec:
    width: float     # mm; em depósito por pontos, é o diâmetro de cada ponto
    height: float    # mm, altura do cordão por camada
    density: float   # g/cm³ do material depositado


class DepositionMode(ProcessMode):
    key = "deposicao"
    name = "Deposição (WAAM)"

    def __init__(self, bead: BeadSpec) -> None:
        self.bead = bead

    def is_work(self, move: Move) -> bool:
        # deposita sempre que o processo está ligado, inclusive em esperas com arco aceso
        return move.active and not move.rapid

    def validate(self, moves: list[Move]) -> list[Issue]:
        if moves and not any(m.active for m in moves):
            return [Issue(
                moves[0].line, WARNING,
                "nenhum depósito encontrado: nenhum movimento com processo ligado. "
                "Verifique o dialeto (códigos de liga/desliga do arco)",
            )]
        issues = self._rapid_with_process_on(moves)
        layer_issue = self._layer_height_issue(moves)
        if layer_issue is not None:
            issues.append(layer_issue)
        return issues

    def cards(self, toolpath: Toolpath) -> list[ModeCard]:
        work = toolpath.is_cut
        if not work.any():
            return []

        lengths = np.linalg.norm(toolpath.ends - toolpath.starts, axis=1)
        bead_length = float(lengths[work].sum())
        dots = int((work & toolpath.is_dwell).sum())
        volume = self.deposited_volume(bead_length, dots)
        mass_kg = volume * self.bead.density / 1e6  # mm³ → cm³ → g → kg

        arc_time = float(toolpath.durations[toolpath.active].sum())
        rate = mass_kg / (arc_time / 3600) if arc_time > 0 else 0.0

        return [
            ModeCard("Material depositado", f"{mass_kg:.3f} kg",
                     f"{volume / MM3_PER_CM3:.1f} cm³ · densidade {self.bead.density:g} g/cm³"),
            ModeCard("Taxa de deposição", f"{rate:.2f} kg/h",
                     f"em {format_duration(arc_time)} com arco ligado"),
            ModeCard("Trajeto depositado", format_length(bead_length),
                     f"{dots} pontos depositados"),
        ]

    def deposited_volume(self, bead_length: float, dots: int) -> float:
        """Volume em mm³. Cordão: comprimento × largura × altura. Ponto: cilindro de diâmetro = largura."""
        w, h = self.bead.width, self.bead.height
        return bead_length * w * h + dots * math.pi / 4 * w * w * h

    # --- validação ---

    @staticmethod
    def _rapid_with_process_on(moves: list[Move]) -> list[Issue]:
        lines = sorted({m.line for m in moves if m.rapid and m.active})
        return [Issue(line, ERROR, "deslocamento rápido (G0) com processo ligado")
                for line in lines]

    def _layer_height_issue(self, moves: list[Move]) -> Issue | None:
        work = [m for m in moves if m.is_cut]
        levels = sorted({round(m.end[2], 3) for m in work})
        if len(levels) < 2:
            return None
        step = float(np.median(np.diff(levels)))
        if abs(step - self.bead.height) <= HEIGHT_TOLERANCE:
            return None
        return Issue(
            work[0].line, WARNING,
            f"passo entre camadas de {step:.2f} mm; "
            f"cordão configurado com {self.bead.height:.2f} mm",
        )