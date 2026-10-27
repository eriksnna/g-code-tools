"""Verificações de segurança antes de interpretar um arquivo G-code.

G-code é entrada não confiável: pode vir de qualquer origem. Este módulo recusa
arquivos fora de limites razoáveis antes que o parser/expander gastem memória ou
tempo com eles. Não depende de Qt.
"""
from __future__ import annotations

from pathlib import Path

import config


class UnsafeFileError(ValueError):
    """O arquivo foi recusado por exceder um limite de segurança."""


def check_file_size(path: Path) -> None:
    size = path.stat().st_size
    if size > config.MAX_FILE_SIZE_BYTES:
        raise UnsafeFileError(
            f"Arquivo tem {size / 1_048_576:.1f} MB, acima do limite de "
            f"{config.MAX_FILE_SIZE_BYTES / 1_048_576:.0f} MB."
        )


def check_line_lengths(text: str) -> None:
    for lineno, line in enumerate(text.splitlines(), start=1):
        if len(line) > config.MAX_LINE_LENGTH:
            raise UnsafeFileError(
                f"Linha {lineno} tem {len(line)} caracteres, acima do limite de "
                f"{config.MAX_LINE_LENGTH}. O arquivo pode estar corrompido."
            )