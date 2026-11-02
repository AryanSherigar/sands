from uuid import UUID, uuid4

from httpx import AsyncClient
from tests.repositories.helpers import OWNER_USER_ID
from tests.services.helpers import mutation
from tests.services.test_campaign_service import initialization

INTERNAL = {"X-Internal-Service-Token": "internal"}
RIVAL = "house_ashford"
LONG_PACT_TURNS = 12


async def _start(api: AsyncClient) -> tuple[str, int]:
    request = initialization().model_dump(mode="json")
    created = await api.post(
        "/internal/v1/playthroughs", json=request, headers=INTERNAL
    )
    return f"/v1/playthroughs/{request['playthrough_id']}", created.json()[
        "world_version"
    ]


async def _open(api: AsyncClient, base: str, version: int, operation: str = "talk"):
    body = mutation(operation, version).model_dump() | {"counterpart_faction_id": RIVAL}
    return await api.post(f"{base}/scenes/negotiation", json=body)


def _internal(scene_id: str, acting_user: UUID) -> tuple[str, dict[str, str]]:
    return f"/internal/v1/scenes/{scene_id}", INTERNAL | {
        "X-Acting-User-Id": str(acting_user)
    }


def _exchange(sequence: int, action: str = "continue_talk", duration=None) -> dict:
    return {
        "sequence": sequence,
        "player_text": f"player {sequence}",
        "leader_text": f"leader {sequence}",
        "decision": {"action": action, "duration_turns": duration},
    }


async def _scene(api: AsyncClient):
    base, version = await _start(api)
    opened = await _open(api, base, version)
    scene_id = opened.json()["scene_id"]
    path, headers = _internal(scene_id, OWNER_USER_ID)
    return base, opened.json(), scene_id, path, headers


async def test_opening_pauses_the_turn_and_blocks_end_turn_and_orders(
    api: AsyncClient,
) -> None:
    base, version = await _start(api)
    opened = await _open(api, base, version)
    assert opened.status_code == 200
    assert opened.json()["status"] == "awaiting_scene"
    assert opened.json()["scene_id"] is not None
    version = opened.json()["world_version"]
    ended = await api.post(
        f"{base}/end-turn", json=mutation("end", version).model_dump()
    )
    assert ended.status_code == 409
    assert ended.json()["code"] == "scene_pending"
    second = await _open(api, base, version, "talk-again")
    assert second.status_code == 409


async def test_opening_is_idempotent_and_rejects_the_player_faction(
    api: AsyncClient,
) -> None:
    base, version = await _start(api)
    first = await _open(api, base, version)
    again = await _open(api, base, version)
    assert again.json() == first.json()
    body = mutation("self", first.json()["world_version"]).model_dump()
    refused = await api.post(
        f"{base}/scenes/negotiation",
        json=body | {"counterpart_faction_id": "house_carrow"},
    )
    assert refused.status_code in (409, 422)


async def test_browser_view_hides_the_hidden_limits(api: AsyncClient) -> None:
    base, _, scene_id, _, _ = await _scene(api)
    view = await api.get(f"{base}/scenes/{scene_id}")
    assert view.status_code == 200
    body = view.json()
    assert body["status"] == "pending"
    assert body["exchanges_remaining"] == 6
    assert body["participants"][0]["name"]
    assert "hidden_limits" not in view.text
    assert "acceptance" not in view.text
    assert (await api.get(f"{base}/scenes/{uuid4()}")).status_code == 404


async def test_internal_routes_need_the_service_token_and_the_owner(
    api: AsyncClient,
) -> None:
    _, _, _, path, headers = await _scene(api)
    assert (await api.get(f"{path}/package")).status_code == 401
    stranger = {**headers, "X-Acting-User-Id": str(uuid4())}
    assert (await api.get(f"{path}/package", headers=stranger)).status_code == 404
    package = await api.get(f"{path}/package", headers=headers)
    assert package.status_code == 200
    assert package.json()["package"]["hidden_limits"]["acceptance"] is not None
    assert package.json()["status"] == "opened"


async def test_exchanges_are_ordered_idempotent_and_survive_a_refresh(
    api: AsyncClient,
) -> None:
    base, _, scene_id, path, headers = await _scene(api)
    first = await api.post(f"{path}/exchanges", json=_exchange(1), headers=headers)
    assert first.json()["status"] == "accepted"
    assert first.json()["exchanges_remaining"] == 5
    retry = await api.post(f"{path}/exchanges", json=_exchange(1), headers=headers)
    assert retry.json()["status"] == "duplicate_ignored"
    gap = await api.post(f"{path}/exchanges", json=_exchange(3), headers=headers)
    assert gap.json()["status"] == "rejected"
    view = await api.get(f"{base}/scenes/{scene_id}")
    assert [item["player_text"] for item in view.json()["transcript"]] == ["player 1"]


async def test_a_proposal_inside_the_range_can_be_confirmed(api: AsyncClient) -> None:
    base, opened, scene_id, path, headers = await _scene(api)
    proposed = await api.post(
        f"{path}/exchanges",
        json=_exchange(1, "propose_terms", LONG_PACT_TURNS),
        headers=headers,
    )
    card = proposed.json()["pending_proposal"]
    assert card["terms"][0]["kind"] == "non_aggression"
    assert card["is_confirmed_by_player"] is False
    decision = mutation("confirm", opened["world_version"]).model_dump() | {
        "is_confirmed": True,
        "proposal_sequence": 1,
    }
    done = await api.post(f"{base}/scenes/{scene_id}/decision", json=decision)
    assert done.status_code == 200
    assert done.json()["status"] == "planning"
    view = await api.get(f"{base}/scenes/{scene_id}")
    assert view.json()["status"] == "resolved"
    assert view.json()["outcome"]["result"] == "agreed"
    again = await api.post(f"{base}/scenes/{scene_id}/decision", json=decision)
    assert again.json() == done.json()


async def test_a_proposal_below_the_range_is_not_offered(api: AsyncClient) -> None:
    _, _, _, path, headers = await _scene(api)
    result = await api.post(
        f"{path}/exchanges", json=_exchange(1, "propose_terms", 1), headers=headers
    )
    assert result.json()["pending_proposal"] is None
    assert result.json()["reason"] == "outside_limits"


async def test_walk_out_ends_the_scene_and_unblocks_planning(api: AsyncClient) -> None:
    base, _, scene_id, path, headers = await _scene(api)
    ended = await api.post(
        f"{path}/exchanges", json=_exchange(1, "walk_out"), headers=headers
    )
    assert ended.json()["scene_status"] == "resolved"
    view = await api.get(f"{base}/scenes/{scene_id}")
    assert view.json()["outcome"]["result"] == "walked_out"
    world = await api.get(f"{base}/world")
    assert world.json()["status"] == "planning"
    late = await api.post(f"{path}/exchanges", json=_exchange(2), headers=headers)
    assert late.json()["status"] == "rejected"


async def test_reaching_the_cap_without_terms_defaults_to_refusal(
    api: AsyncClient,
) -> None:
    base, _, scene_id, path, headers = await _scene(api)
    for sequence in range(1, 7):
        await api.post(f"{path}/exchanges", json=_exchange(sequence), headers=headers)
    view = await api.get(f"{base}/scenes/{scene_id}")
    assert view.json()["status"] == "defaulted"
    assert view.json()["outcome"]["result"] == "refused"


async def test_declining_or_abandoning_resolves_as_a_refusal(api: AsyncClient) -> None:
    base, opened, scene_id, _, _ = await _scene(api)
    decision = mutation("abandon", opened["world_version"]).model_dump() | {
        "is_confirmed": False
    }
    done = await api.post(f"{base}/scenes/{scene_id}/decision", json=decision)
    assert done.status_code == 200
    view = await api.get(f"{base}/scenes/{scene_id}")
    assert (view.json()["status"], view.json()["outcome"]["result"]) == (
        "defaulted",
        "refused",
    )


async def test_confirming_without_a_proposal_is_refused(api: AsyncClient) -> None:
    base, opened, scene_id, _, _ = await _scene(api)
    decision = mutation("confirm", opened["world_version"]).model_dump() | {
        "is_confirmed": True,
        "proposal_sequence": 1,
    }
    result = await api.post(f"{base}/scenes/{scene_id}/decision", json=decision)
    assert result.status_code == 422


async def test_replay_verification_still_passes_after_a_confirmed_pact(
    api: AsyncClient,
) -> None:
    base, opened, scene_id, path, headers = await _scene(api)
    await api.post(
        f"{path}/exchanges",
        json=_exchange(1, "propose_terms", LONG_PACT_TURNS),
        headers=headers,
    )
    decision = mutation("confirm", opened["world_version"]).model_dump() | {
        "is_confirmed": True,
        "proposal_sequence": 1,
    }
    done = await api.post(f"{base}/scenes/{scene_id}/decision", json=decision)
    ended = await api.post(
        f"{base}/end-turn",
        json=mutation("end", done.json()["world_version"]).model_dump(),
    )
    assert ended.status_code == 200
    verified = await api.post(f"{base}/replay/verify")
    assert verified.status_code == 200
    assert verified.json()["step_count"] >= 3


async def test_world_view_lists_rivals_with_rough_ranges_and_confirmed_pacts(
    api: AsyncClient,
) -> None:
    base, opened, scene_id, path, headers = await _scene(api)
    before = (await api.get(f"{base}/world")).json()
    rival = next(item for item in before["rivals"] if item["faction_id"] == RIVAL)
    assert rival["relation"] == "peace"
    assert rival["treasury_range"]["high"] - rival["treasury_range"]["low"] == 50
    assert before["pacts"] == []
    await api.post(
        f"{path}/exchanges",
        json=_exchange(1, "propose_terms", LONG_PACT_TURNS),
        headers=headers,
    )
    decision = mutation("confirm", opened["world_version"]).model_dump() | {
        "is_confirmed": True,
        "proposal_sequence": 1,
    }
    await api.post(f"{base}/scenes/{scene_id}/decision", json=decision)
    after = (await api.get(f"{base}/world")).json()
    assert [pact["faction_b"] for pact in after["pacts"]] == [RIVAL]
    assert after["pacts"][0]["end_turn"] == LONG_PACT_TURNS


async def test_confirming_a_card_that_was_replaced_is_refused(
    api: AsyncClient,
) -> None:
    base, opened, scene_id, path, headers = await _scene(api)
    await api.post(
        f"{path}/exchanges",
        json=_exchange(1, "propose_terms", LONG_PACT_TURNS),
        headers=headers,
    )
    await api.post(f"{path}/exchanges", json=_exchange(2), headers=headers)
    stale = mutation("stale-confirm", opened["world_version"]).model_dump() | {
        "is_confirmed": True,
        "proposal_sequence": 1,
    }
    result = await api.post(f"{base}/scenes/{scene_id}/decision", json=stale)
    assert (result.status_code, result.json()["code"]) == (422, "no_proposal")


async def test_confirming_the_wrong_sequence_reports_changed_terms(
    api: AsyncClient,
) -> None:
    base, opened, scene_id, path, headers = await _scene(api)
    await api.post(
        f"{path}/exchanges",
        json=_exchange(1, "propose_terms", LONG_PACT_TURNS),
        headers=headers,
    )
    await api.post(
        f"{path}/exchanges",
        json=_exchange(2, "propose_terms", LONG_PACT_TURNS - 1),
        headers=headers,
    )
    view = (await api.get(f"{base}/scenes/{scene_id}")).json()
    assert view["pending_proposal_sequence"] == 2
    wrong = mutation("wrong-sequence", opened["world_version"]).model_dump() | {
        "is_confirmed": True,
        "proposal_sequence": 1,
    }
    result = await api.post(f"{base}/scenes/{scene_id}/decision", json=wrong)
    assert (result.status_code, result.json()["code"]) == (409, "terms_changed")


async def test_confirming_without_naming_the_card_is_rejected(
    api: AsyncClient,
) -> None:
    base, opened, scene_id, _, _ = await _scene(api)
    body = mutation("anonymous", opened["world_version"]).model_dump() | {
        "is_confirmed": True
    }
    result = await api.post(f"{base}/scenes/{scene_id}/decision", json=body)
    assert result.status_code == 422


async def test_a_multi_clause_card_is_priced_proposed_and_signed(
    api: AsyncClient,
) -> None:
    base, opened, scene_id, path, headers = await _scene(api)
    terms = [
        {
            "kind": "non_aggression",
            "faction_a": "house_carrow",
            "faction_b": RIVAL,
            "duration_turns": LONG_PACT_TURNS,
        },
        {
            "kind": "trade_deal",
            "faction_a": "house_carrow",
            "faction_b": RIVAL,
            "duration_turns": LONG_PACT_TURNS,
        },
    ]
    exchange = _exchange(1, "propose_terms") | {
        "decision": {"action": "propose_terms", "terms": terms}
    }

    proposed = await api.post(f"{path}/exchanges", json=exchange, headers=headers)

    body = proposed.json()
    assert [term["kind"] for term in body["pending_proposal"]["terms"]] == [
        "non_aggression",
        "trade_deal",
    ]
    assert body["verdict"] == "accept"
    assert body["clause_bands"] and "accept_at" not in str(body)
    decision = mutation("confirm", opened["world_version"]).model_dump() | {
        "is_confirmed": True,
        "proposal_sequence": 1,
    }
    done = await api.post(f"{base}/scenes/{scene_id}/decision", json=decision)
    assert done.status_code == 200


async def test_a_card_that_only_bargains_reports_the_haggle_verdict(
    api: AsyncClient,
) -> None:
    base, _, scene_id, path, headers = await _scene(api)
    terms = [
        {
            "kind": "non_aggression",
            "faction_a": "house_carrow",
            "faction_b": RIVAL,
            "duration_turns": 4,
        }
    ]
    exchange = _exchange(1) | {"decision": {"action": "propose_terms", "terms": terms}}

    result = await api.post(f"{path}/exchanges", json=exchange, headers=headers)

    assert result.json()["pending_proposal"] is None
    assert result.json()["verdict"] in {"haggle", "refuse"}
    view = await api.get(f"{base}/scenes/{scene_id}")
    assert view.json()["transcript"][0]["verdict"] == result.json()["verdict"]
