"""Ícones da interface via QtAwesome (fonte vetorial Font Awesome).

Em vez de emojis (inconsistentes entre fontes do SO) ou ícones nativos do Qt
(que variam de estilo em estilo — foi o que deu errado no botão de ajuda),
usamos uma fonte de ícones vetorial com cor fixa: resultado consistente em
qualquer Windows, sem depender do tema do sistema.
"""
from __future__ import annotations

import qtawesome as qta
from PySide6.QtGui import QIcon

from ui.theme import ICON_COLOR

PLAY = "fa5s.play"
PAUSE = "fa5s.pause"
SKIP_BACK = "fa5s.step-backward"
SKIP_FORWARD = "fa5s.step-forward"
REWIND = "fa5s.fast-backward"
FAST_FORWARD = "fa5s.fast-forward"
HELP = "fa5s.question"
CLOSE = "fa5s.times"
NEW_FILE = "fa5s.file"
OPEN_FILE = "fa5s.folder-open"
SAVE = "fa5s.save"
DISCARD = "fa5s.ban"
QUIT = "fa5s.sign-out-alt"
APPLY = "fa5s.check"
SEARCH = "fa5s.search"
SETTINGS = "fa5s.cog"


def icon(name: str, color: str = ICON_COLOR) -> QIcon:
    """Ícone vetorial pelo nome QtAwesome (ex.: 'fa5s.play'), tingido com `color`."""
    return qta.icon(name, color=color)