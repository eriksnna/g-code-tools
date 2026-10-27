from core.dialect import DIALECT_CHOICES, DIALECTS, get_dialect


def test_dialect_choices_cover_all_registered_dialects():
    assert len(DIALECT_CHOICES) == len(DIALECTS)
    for _label, key in DIALECT_CHOICES:
        assert get_dialect(key) is DIALECTS[key]


def test_dialect_choices_labels_are_dialect_names():
    for label, key in DIALECT_CHOICES:
        assert label == DIALECTS[key].name