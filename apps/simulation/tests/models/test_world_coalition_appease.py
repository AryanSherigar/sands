from app.models.world_coalition import CoalitionWorldState, pair_key


def test_empty_appease_state_is_not_serialized() -> None:
    document = CoalitionWorldState().model_dump()

    assert "appease_cooldowns" not in document
    assert "rejoin_lockouts" not in document


def test_filled_appease_state_round_trips() -> None:
    state = CoalitionWorldState(
        appease_cooldowns={pair_key("aa", "bb"): 4},
        rejoin_lockouts={pair_key("aa", "cc"): 7},
    )

    restored = CoalitionWorldState.model_validate(state.model_dump())

    assert restored == state
    assert restored.appease_cooldowns == {"aa:bb": 4}
