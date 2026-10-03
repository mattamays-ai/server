from music_assistant.models.smart_fades import SmartFadesMode, SmartFadesProfile


def test_expanded_smart_fade_modes_exist() -> None:
    assert SmartFadesMode.LONG_BLEND.value == "long_blend"
    assert SmartFadesMode.SHORT_BLEND.value == "short_blend"
    assert SmartFadesMode.VOCAL_SAFE.value == "vocal_safe"
    assert SmartFadesMode.TEMPO_MATCH.value == "tempo_match"
    assert SmartFadesMode.CLEAN_BLEND.value == "clean_blend"


def test_profiles_exist() -> None:
    assert SmartFadesProfile.HARMONIC.value == "harmonic"
    assert SmartFadesProfile.VOCAL_SAFE.value == "vocal_safe"
