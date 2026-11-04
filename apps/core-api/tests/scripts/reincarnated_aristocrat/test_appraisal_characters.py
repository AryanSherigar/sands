import pytest
from scripts.reincarnated_aristocrat import characters, stats
from scripts.reincarnated_aristocrat.characters import CHARACTERS, WIKI_CAP_SLUGS


def _by_slug(slug: str) -> characters.CharacterSpec:
    return next(spec for spec in CHARACTERS if spec.slug == slug)


def test_roster_is_the_ten_canon_characters() -> None:
    assert len(CHARACTERS) == 10
    assert len({spec.slug for spec in CHARACTERS}) == 10
    assert len(characters.RECRUITABLE_SLUGS) == 6
    assert set(characters.RECRUITABLE_SLUGS) == {
        "ritsu",
        "charlotte",
        "rosell",
        "lysia",
        "mireille",
        "fahm",
    }


def test_every_character_has_every_stat_and_aptitude() -> None:
    for spec in CHARACTERS:
        assert set(spec.stats) == set(stats.STAT_KEYS)
        assert len(spec.aptitudes) == len(stats.APTITUDE_KEYS)
        assert set(spec.aptitudes) <= set(stats.RANKS)


def test_traits_are_known() -> None:
    assert {spec.trait for spec in CHARACTERS} <= set(characters.TRAIT_NOTES)


def test_starting_values_never_exceed_their_hidden_cap() -> None:
    for spec in CHARACTERS:
        for key, value in spec.stats.items():
            cap = stats.stat_cap(key, value, spec.is_adult)
            assert 0 <= value.start <= cap <= stats.STAT_CEILING, (spec.slug, key)


def test_wiki_caps_are_used_where_the_wiki_lists_them() -> None:
    ritsu = characters.attributes_schema(_by_slug("ritsu"))
    assert ritsu["leadership"].max == 99
    assert ritsu["prowess"].max == 90
    charlotte = characters.attributes_schema(_by_slug("charlotte"))
    assert charlotte["prowess"].max == 116
    assert characters.attributes_schema(_by_slug("mireille"))["courage"].max == 72
    assert {"ritsu", "charlotte", "rosell", "mireille"} == WIKI_CAP_SLUGS


def test_ambition_and_loyalty_use_the_percent_scale() -> None:
    for spec in CHARACTERS:
        schema = characters.attributes_schema(spec)
        assert schema["ambition"].max == stats.PERCENT_CEILING
        assert schema["loyalty"].max == stats.PERCENT_CEILING


@pytest.mark.parametrize(
    ("start", "is_adult", "expected"),
    [(40, False, 60), (8, False, 18), (62, True, 71), (115, False, 120)],
)
def test_cap_formula(start: int, is_adult: bool, expected: int) -> None:
    assert stats.derive_cap(start, is_adult) == expected


def test_only_stats_and_loyalty_reach_the_narrator_each_turn() -> None:
    for spec in CHARACTERS:
        visible = {
            key
            for key, value in characters.attributes_schema(spec).items()
            if value.is_narrator_visible
        }
        assert visible == {*stats.STAT_KEYS, "loyalty"}


def test_narrator_note_carries_aptitudes_and_the_secrecy_rule() -> None:
    note = characters.narrator_instruction(_by_slug("ritsu"))
    assert "Cavalry S" in note
    assert "Stratagem S" in note
    assert characters.APPRAISAL_NOTE in note
    assert "Ars's age +4" in note


def test_every_entity_seed_is_a_character() -> None:
    seeds = characters.character_seeds()
    assert {seed.payload.entity_type for seed in seeds} == {"character"}
    assert all(seed.payload.narrator_instruction for seed in seeds)
