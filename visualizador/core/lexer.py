"""Leitura básica de linhas de G-code e tipos de problema. Sem Qt e sem numpy."""
from __future__ import annotations

import re
from dataclasses import dataclass

ERROR = "erro"
WARNING = "aviso"

WORD_RE = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")
PAREN_COMMENT_RE = re.compile(r"\(.*?\)")


class GCodeError(ValueError):
    """Linha de G-code que não pode ser interpretada."""


@dataclass(frozen=True)
class Issue:
    """Problema encontrado no arquivo, associado a uma linha."""
    line: int
    severity: str  # ERROR ou WARNING
    message: str


def clean_line(raw: str) -> str:
    """Remove comentários, espaços das pontas e padroniza em maiúsculas."""
    without_parens = PAREN_COMMENT_RE.sub("", raw)
    without_semicolon = without_parens.split(";", 1)[0]
    return without_semicolon.strip().upper()


def parse_words(line: str) -> list[tuple[str, float]]:
    """'G20 G1 X10 Y-2.5' -> [('G', 20.0), ('G', 1.0), ('X', 10.0), ('Y', -2.5)]"""
    return [(letter, float(value)) for letter, value in WORD_RE.findall(line)]