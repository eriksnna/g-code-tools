"""Dialetos de G-code. As diferenças entre controladores ficam aqui, fora do núcleo.

Cada perfil responde a perguntas sobre a máquina: em que unidade o G04 espera e
quais M-codes ligam e desligam o processo (spindle, arco, tocha). Para uma máquina
nova, basta acrescentar um perfil em DIALECTS.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dialect:
    name: str
    dwell_unit: float           # segundos por unidade de P no G04
    process_on: frozenset[int]  # M-codes que ligam o processo
    process_off: frozenset[int] # M-codes que desligam o processo


DIALECTS: dict[str, Dialect] = {
    "generico": Dialect(
        name="Genérico (ISO)",
        dwell_unit=1.0,
        process_on=frozenset({3, 4}),   # M3/M4: spindle
        process_off=frozenset({5}),     # M5: spindle
    ),
    "arco-m8-m9": Dialect(
        name="Arco em M8/M9",
        dwell_unit=1.0,
        process_on=frozenset({8}),
        process_off=frozenset({9}),
    ),
}


def get_dialect(key: str) -> Dialect:
    try:
        return DIALECTS[key]
    except KeyError as err:
        raise ValueError(f"dialeto desconhecido: {key!r}") from err