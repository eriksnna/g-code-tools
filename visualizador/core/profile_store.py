"""Persistência dos perfis de máquina em disco (JSON na pasta de configuração do usuário).

Falha ao ler ou escrever esse arquivo nunca deve travar o app: persistência é uma
conveniência, então qualquer problema (arquivo corrompido, sem permissão de escrita)
cai de volta nos perfis padrão em memória, silenciosamente.
"""
from __future__ import annotations

import json

import config
from core.machine_profile import MachineProfile, default_profiles


def load_profiles() -> tuple[list[MachineProfile], str | None]:
    """Carrega perfis salvos e o nome do perfil ativo. Sem arquivo ou corrompido -> padrões."""
    if not config.PROFILES_FILE.exists():
        return default_profiles(), None
    try:
        data = json.loads(config.PROFILES_FILE.read_text(encoding="utf-8"))
        profiles = [
            MachineProfile(
                name=str(item["name"]),
                limits={
                    axis: (float(bounds[0]), float(bounds[1]))
                    for axis, bounds in item["limits"].items()
                },
            )
            for item in data["profiles"]
        ]
        if not profiles:
            return default_profiles(), None
        return profiles, data.get("active")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, IndexError):
        return default_profiles(), None


def save_profiles(profiles: list[MachineProfile], active_name: str) -> None:
    """Salva perfis e qual está ativo. Erros de escrita são ignorados silenciosamente."""
    payload = {
        "active": active_name,
        "profiles": [
            {"name": p.name, "limits": {axis: list(bounds) for axis, bounds in p.limits.items()}}
            for p in profiles
        ],
    }
    try:
        config.PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.PROFILES_FILE.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass