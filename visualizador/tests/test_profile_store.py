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