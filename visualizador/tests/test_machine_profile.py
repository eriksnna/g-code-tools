from core.machine_profile import DEFAULT_LIMITS, default_profiles


def test_default_profiles_include_my_machine_with_default_limits():
    profiles = default_profiles()
    assert profiles[0].limits == DEFAULT_LIMITS


def test_cloning_a_profile_does_not_share_limits_dict():
    original = default_profiles()[0]
    copy = original.clone()
    copy.limits["X"] = (0.0, 1.0)
    assert original.limits["X"] != (0.0, 1.0)