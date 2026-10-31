from strategy_contracts.scenario import LeaderSetup, PlayerRulerCustomization


def test_leader_setup_accepts_avatar_url():
    leader = LeaderSetup(
        id="mira",
        name="Queen Mira",
        faction_id="dunmere",
        trait_ids=["proud"],
        ambition_ids=["expansion"],
        portrait_url="https://example.com/mira.png",
        avatar_url="https://example.com/mira.mavatar",
    )
    assert leader.avatar_url == "https://example.com/mira.mavatar"
    assert leader.portrait_url == "https://example.com/mira.png"


def test_leader_setup_defaults_avatar_url_to_none():
    leader = LeaderSetup(
        id="aldric",
        name="Duke Aldric",
        faction_id="dunmere",
        trait_ids=["cautious"],
        ambition_ids=["wealth"],
    )
    assert leader.avatar_url is None
    assert leader.portrait_url is None


def test_player_ruler_customization_accepts_avatar_url():
    custom = PlayerRulerCustomization(
        name="Alden IV",
        trait_ids=["cautious", "proud"],
        ambition_ids=["wealth"],
        avatar_url="https://example.com/alden.mavatar",
    )
    assert custom.avatar_url == "https://example.com/alden.mavatar"
