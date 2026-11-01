"""Tests for ingest request/response models."""

from datetime import datetime
from uuid import uuid4

import pytest
from app.models.ingest import (
    AcceptedDelta,
    AcceptedDeltaItem,
    FlushItem,
    IngestItem,
    IngestItemOutcome,
    IngestRequest,
    IngestResponse,
    PlayerEntityPayload,
    RegisterItem,
    RegisterPayload,
    RejectedCall,
    SetupFactPayload,
    TurnItem,
    TurnPayload,
)
from pydantic import ValidationError


class TestAcceptedDeltaItem:
    def test_minimal_item(self) -> None:
        item = AcceptedDeltaItem(
            kind="state_mutation",
            key="test_key",
        )
        assert item.kind == "state_mutation"
        assert item.key == "test_key"
        assert item.before is None
        assert item.after is None
        assert item.detail == {}

    def test_all_fields(self) -> None:
        item = AcceptedDeltaItem(
            kind="automatic_effect",
            key="effect_key",
            before={"old": "value"},
            after={"new": "value"},
            detail={"reason": "test"},
        )
        assert item.kind == "automatic_effect"
        assert item.detail == {"reason": "test"}

    def test_invalid_kind(self) -> None:
        with pytest.raises(ValidationError):
            AcceptedDeltaItem(
                kind="invalid_kind",  # type: ignore
                key="test",
            )


class TestAcceptedDelta:
    def test_empty_items(self) -> None:
        delta = AcceptedDelta()
        assert delta.items == []

    def test_with_items(self) -> None:
        item = AcceptedDeltaItem(kind="state_mutation", key="test")
        delta = AcceptedDelta(items=[item])
        assert len(delta.items) == 1


class TestRejectedCall:
    def test_minimal_call(self) -> None:
        call = RejectedCall(tool_name="test_tool")
        assert call.tool_name == "test_tool"
        assert call.arguments == {}
        assert call.result == {}

    def test_with_args_and_result(self) -> None:
        call = RejectedCall(
            tool_name="test",
            arguments={"arg": "value"},
            result={"res": "value"},
        )
        assert call.arguments == {"arg": "value"}
        assert call.result == {"res": "value"}


class TestPlayerEntityPayload:
    def test_minimal_entity(self) -> None:
        entity_id = uuid4()
        payload = PlayerEntityPayload(
            authored_entity_id=entity_id,
            canonical_name="Hero",
            entity_type="player_character",
        )
        assert payload.authored_entity_id == entity_id
        assert payload.canonical_name == "Hero"
        assert payload.aliases == []

    def test_with_aliases(self) -> None:
        entity_id = uuid4()
        payload = PlayerEntityPayload(
            authored_entity_id=entity_id,
            canonical_name="Hero",
            entity_type="player_character",
            aliases=["The Hero", "Brave One"],
        )
        assert payload.aliases == ["The Hero", "Brave One"]


class TestSetupFactPayload:
    def test_with_object_entity(self) -> None:
        subj_id = uuid4()
        obj_id = uuid4()
        payload = SetupFactPayload(
            fact_id=uuid4(),
            subject_entity_id=subj_id,
            predicate="knows",
            object_entity_id=obj_id,
        )
        assert payload.object_entity_id == obj_id
        assert payload.object_literal is None

    def test_with_object_literal(self) -> None:
        subj_id = uuid4()
        payload = SetupFactPayload(
            fact_id=uuid4(),
            subject_entity_id=subj_id,
            predicate="has_skill",
            object_literal="swordsmanship",
        )
        assert payload.object_entity_id is None
        assert payload.object_literal == "swordsmanship"


class TestRegisterPayload:
    def test_minimal_register(self) -> None:
        payload = RegisterPayload(
            scenario_id=uuid4(),
            publish_revision=1,
        )
        assert payload.player_entity is None
        assert payload.setup_facts == []

    def test_with_player_entity_and_facts(self) -> None:
        scenario_id = uuid4()
        entity_id = uuid4()
        fact_id = uuid4()

        player = PlayerEntityPayload(
            authored_entity_id=entity_id,
            canonical_name="Hero",
            entity_type="player_character",
        )
        fact = SetupFactPayload(
            fact_id=fact_id,
            subject_entity_id=entity_id,
            predicate="location",
            object_literal="tavern",
        )

        payload = RegisterPayload(
            scenario_id=scenario_id,
            publish_revision=2,
            player_entity=player,
            setup_facts=[fact],
        )
        assert payload.player_entity == player
        assert len(payload.setup_facts) == 1


class TestTurnPayload:
    def test_minimal_turn(self) -> None:
        turn_id = uuid4()
        payload = TurnPayload(
            turn_id=turn_id,
            turn_number=1,
            participant_id=uuid4(),
            action_mode="normal",
        )
        assert payload.turn_id == turn_id
        assert payload.turn_number == 1
        assert payload.action_text == ""
        assert payload.narration_text == ""

    def test_with_deltas_and_rejected(self) -> None:
        delta_item = AcceptedDeltaItem(kind="state_mutation", key="test")
        rejected = RejectedCall(tool_name="test_tool")

        payload = TurnPayload(
            turn_id=uuid4(),
            turn_number=5,
            participant_id=uuid4(),
            action_mode="fast",
            action_text="attack",
            narration_text="You strike!",
            accepted_delta=AcceptedDelta(items=[delta_item]),
            rejected_calls=[rejected],
            created_at=datetime.now(),
        )
        assert payload.turn_number == 5
        assert len(payload.accepted_delta.items) == 1
        assert len(payload.rejected_calls) == 1


class TestRegisterItem:
    def test_register_item_minimal(self) -> None:
        payload = RegisterPayload(
            scenario_id=uuid4(),
            publish_revision=1,
        )
        item = RegisterItem(
            item_kind="register_playthrough",
            sequence=0,
            payload=payload,
        )
        assert item.item_kind == "register_playthrough"
        assert item.sequence == 0

    def test_register_sequence_must_be_zero(self) -> None:
        payload = RegisterPayload(
            scenario_id=uuid4(),
            publish_revision=1,
        )
        with pytest.raises(ValidationError):
            RegisterItem(
                item_kind="register_playthrough",
                sequence=1,  # Must be 0
                payload=payload,
            )


class TestTurnItem:
    def test_turn_item_sequence_equals_turn_number(self) -> None:
        turn_id = uuid4()
        payload = TurnPayload(
            turn_id=turn_id,
            turn_number=3,
            participant_id=uuid4(),
            action_mode="normal",
        )
        item = TurnItem(
            item_kind="turn",
            sequence=3,
            payload=payload,
        )
        assert item.sequence == 3
        assert item.payload.turn_number == 3

    def test_turn_item_sequence_mismatch_rejected(self) -> None:
        turn_id = uuid4()
        payload = TurnPayload(
            turn_id=turn_id,
            turn_number=3,
            participant_id=uuid4(),
            action_mode="normal",
        )
        with pytest.raises(ValidationError):
            TurnItem(
                item_kind="turn",
                sequence=2,  # Doesn't match turn_number
                payload=payload,
            )


class TestFlushItem:
    def test_flush_item_valid(self) -> None:
        item = FlushItem(
            item_kind="flush",
            sequence=5,
        )
        assert item.item_kind == "flush"
        assert item.sequence == 5


class TestIngestItemUnion:
    def test_discriminator_register(self) -> None:
        payload = RegisterPayload(
            scenario_id=uuid4(),
            publish_revision=1,
        )
        register_item = RegisterItem(
            item_kind="register_playthrough",
            sequence=0,
            payload=payload,
        )
        items: list[IngestItem] = [register_item]
        assert items[0].item_kind == "register_playthrough"

    def test_discriminator_turn(self) -> None:
        payload = TurnPayload(
            turn_id=uuid4(),
            turn_number=1,
            participant_id=uuid4(),
            action_mode="normal",
        )
        turn_item = TurnItem(
            item_kind="turn",
            sequence=1,
            payload=payload,
        )
        items: list[IngestItem] = [turn_item]
        assert items[0].item_kind == "turn"

    def test_discriminator_flush(self) -> None:
        flush_item = FlushItem(
            item_kind="flush",
            sequence=2,
        )
        items: list[IngestItem] = [flush_item]
        assert items[0].item_kind == "flush"


class TestIngestRequest:
    def test_minimal_request(self) -> None:
        playthrough_id = uuid4()
        payload = RegisterPayload(
            scenario_id=uuid4(),
            publish_revision=1,
        )
        register = RegisterItem(
            item_kind="register_playthrough",
            sequence=0,
            payload=payload,
        )
        request = IngestRequest(
            playthrough_id=playthrough_id,
            items=[register],
        )
        assert request.playthrough_id == playthrough_id
        assert len(request.items) == 1

    def test_empty_items_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IngestRequest(
                playthrough_id=uuid4(),
                items=[],  # Must have at least one item
            )

    def test_multiple_items(self) -> None:
        playthrough_id = uuid4()
        register = RegisterItem(
            item_kind="register_playthrough",
            sequence=0,
            payload=RegisterPayload(
                scenario_id=uuid4(),
                publish_revision=1,
            ),
        )
        turn = TurnItem(
            item_kind="turn",
            sequence=1,
            payload=TurnPayload(
                turn_id=uuid4(),
                turn_number=1,
                participant_id=uuid4(),
                action_mode="normal",
            ),
        )
        request = IngestRequest(
            playthrough_id=playthrough_id,
            items=[register, turn],
        )
        assert len(request.items) == 2


class TestIngestResponse:
    def test_response_construction(self) -> None:
        playthrough_id = uuid4()
        outcome = IngestItemOutcome(
            item_kind="register_playthrough",
            sequence=0,
            outcome="applied",
        )
        response = IngestResponse(
            playthrough_id=playthrough_id,
            ingested_seq=0,
            latest_seq_seen=0,
            items=[outcome],
        )
        assert response.playthrough_id == playthrough_id
        assert response.ingested_seq == 0
        assert len(response.items) == 1


class TestItemKindOrder:
    def test_item_kind_order_constant(self) -> None:
        from app.models.ingest import ITEM_KIND_ORDER

        assert ITEM_KIND_ORDER["register_playthrough"] == 0
        assert ITEM_KIND_ORDER["turn"] == 1
        assert ITEM_KIND_ORDER["participants"] == 2
        assert ITEM_KIND_ORDER["flush"] == 3
