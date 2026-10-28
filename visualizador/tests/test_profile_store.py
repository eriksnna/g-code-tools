import config
from core.machine_profile import MachineProfile
from core.profile_store import load_profiles, save_profiles


def test_missing_file_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILES_FILE", tmp_path / "profiles.json")
    profiles, active = load_profiles()
    assert len(profiles) >= 1
    assert active is None


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILES_FILE", tmp_path / "profiles.json")
    profiles = [MachineProfile(name="Teste", limits={"X": (0.0, 100.0), "Y": (0.0, 50.0), "Z": (0.0, 25.0)})]
    save_profiles(profiles, "Teste")

    loaded, active = load_profiles()
    assert active == "Teste"
    assert len(loaded) == 1
    assert loaded[0].name == "Teste"
    assert loaded[0].limits["X"] == (0.0, 100.0)


def test_corrupted_file_falls_back_to_defaults(tmp_path, monkeypatch):
    path = tmp_path / "profiles.json"
    path.write_text("isso não é json válido {{{")
    monkeypatch.setattr(config, "PROFILES_FILE", path)
    profiles, active = load_profiles()
    assert len(profiles) >= 1
    assert active is None

def test_roundtrip_preserves_mode_and_dialect(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROFILES_FILE", tmp_path / "profiles.json")
    profiles = [
        MachineProfile(
            name="WAAM",
            limits={"X": (0.0, 100.0), "Y": (0.0, 50.0), "Z": (0.0, 25.0)},
            mode_key="deposicao",
            dialect_key="arco-m8-m9",
        )
    ]
    save_profiles(profiles, "WAAM")

    loaded, active = load_profiles()
    assert active == "WAAM"
    assert loaded[0].mode_key == "deposicao"
    assert loaded[0].dialect_key == "arco-m8-m9"


def test_old_format_file_without_mode_dialect_falls_back_to_defaults(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(config, "PROFILES_FILE", tmp_path / "profiles.json")
    old_format = {
        "active": "Minha máquina",
        "profiles": [
            {"name": "Minha máquina", "limits": {"X": [0.0, 300.0], "Y": [0.0, 200.0], "Z": [-100.0, 100.0]}}
        ],
    }
    config.PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.PROFILES_FILE.write_text(json.dumps(old_format), encoding="utf-8")

    loaded, active = load_profiles()
    assert active == "Minha máquina"
    assert loaded[0].mode_key == config.DEFAULT_MODE
    assert loaded[0].dialect_key == config.DEFAULT_DIALECT