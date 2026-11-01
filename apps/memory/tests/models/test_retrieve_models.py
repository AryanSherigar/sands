"""Tests for app.models.retrieve Pydantic models."""

from uuid import uuid4

import pytest
from app.models.retrieve import (
    MAX_ACTION_TEXT_CHARS,
    MAX_ID_LIST_LENGTH,
    MAX_LAST_UTTERANCE_CHARS,
    MAX_PARTICIPANT_NAME_CHARS,
    MAX_PARTICIPANT_NAMES,
    MAX_RECALL_BUDGET_TOKENS,
    MAX_RECENT_TEXT_CHARS,
    MAX_SCENE_ENTITY_IDS,
    MIN_RECALL_BUDGET_TOKENS,
    ActiveEntity,
    ExtractionContext,
    MemoryItem,
    RetrieveRequest,
    RetrieveResponse,
    SceneAtSequence,
    Watermarks,
)
from pydantic import ValidationError


@pytest.fixture
def valid_retrieve_request() -> dict:
    return {
        "playthrough_id": uuid4(),
        "sequence": 10,
        "action_text": "I search the room",
        "action_mode": "do",
        "actor_participant_id": uuid4(),
        "recent_text": "Earlier we found a key.",
    }


class TestRetrieveRequestValidation:
    def test_valid_minimal_request(self, valid_retrieve_request: dict) -> None:
        req = RetrieveRequest(**valid_retrieve_request)
        assert req.playthrough_id
        assert req.sequence == 10
        assert req.recent_window_turns is None
        assert req.recall_budget_tokens is None
        assert req.last_actor_utterance == ""
        assert req.scene_authored_entity_ids == []
        assert req.revealed_fact_ids == []
        assert req.active_conditional_fact_ids == []
        assert req.participant_names == {}
        assert req.interlocutor_authored_entity_id is None

    def test_action_text_too_long(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["action_text"] = "x" * (MAX_ACTION_TEXT_CHARS + 1)
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "action_text" in str(exc_info.value)

    def test_recent_text_too_long(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["recent_text"] = "x" * (MAX_RECENT_TEXT_CHARS + 1)
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "recent_text" in str(exc_info.value)

    def test_last_actor_utterance_too_long(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["last_actor_utterance"] = "x" * (
            MAX_LAST_UTTERANCE_CHARS + 1
        )
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "last_actor_utterance" in str(exc_info.value)

    def test_scene_entity_ids_exceeds_max(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["scene_authored_entity_ids"] = [
            uuid4() for _ in range(MAX_SCENE_ENTITY_IDS + 1)
        ]
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "scene_authored_entity_ids" in str(exc_info.value)

    def test_revealed_fact_ids_exceeds_max(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["revealed_fact_ids"] = [
            uuid4() for _ in range(MAX_ID_LIST_LENGTH + 1)
        ]
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "revealed_fact_ids" in str(exc_info.value)

    def test_active_conditional_fact_ids_exceeds_max(
        self, valid_retrieve_request: dict
    ) -> None:
        valid_retrieve_request["active_conditional_fact_ids"] = [
            uuid4() for _ in range(MAX_ID_LIST_LENGTH + 1)
        ]
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "active_conditional_fact_ids" in str(exc_info.value)

    def test_recall_budget_too_low(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["recall_budget_tokens"] = MIN_RECALL_BUDGET_TOKENS - 1
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "recall_budget_tokens" in str(exc_info.value)

    def test_recall_budget_too_high(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["recall_budget_tokens"] = MAX_RECALL_BUDGET_TOKENS + 1
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "recall_budget_tokens" in str(exc_info.value)

    def test_sequence_negative(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["sequence"] = -1
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "sequence" in str(exc_info.value)

    def test_participant_names_exceeds_max_entries(
        self, valid_retrieve_request: dict
    ) -> None:
        valid_retrieve_request["participant_names"] = {
            uuid4(): f"Player {i}" for i in range(MAX_PARTICIPANT_NAMES + 1)
        }
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "participant_names" in str(exc_info.value)

    def test_participant_name_too_long(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["participant_names"] = {
            uuid4(): "x" * (MAX_PARTICIPANT_NAME_CHARS + 1)
        }
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "participant_names" in str(exc_info.value)

    def test_unknown_extra_field_rejected(self, valid_retrieve_request: dict) -> None:
        valid_retrieve_request["unknown_field"] = "should fail"
        with pytest.raises(ValidationError) as exc_info:
            RetrieveRequest(**valid_retrieve_request)
        assert "unknown_field" in str(exc_info.value)

    def test_valid_with_all_fields(self, valid_retrieve_request: dict) -> None:
        entity_id_1 = uuid4()
        entity_id_2 = uuid4()
        interlocutor_id = uuid4()
        participant_1_id = uuid4()
        participant_2_id = uuid4()

        valid_retrieve_request.update(
            {
                "scene_authored_entity_ids": [entity_id_1, entity_id_2],
                "interlocutor_authored_entity_id": interlocutor_id,
                "revealed_fact_ids": [uuid4() for _ in range(5)],
                "active_conditional_fact_ids": [uuid4() for _ in range(3)],
                "participant_names": {
                    participant_1_id: "Alice",
                    participant_2_id: "Bob",
                },
                "recent_window_turns": 8,
                "recall_budget_tokens": 3000,
                "last_actor_utterance": "Tell me more.",
            }
        )

        req = RetrieveRequest(**valid_retrieve_request)
        assert req.scene_authored_entity_ids == [entity_id_1, entity_id_2]
        assert req.interlocutor_authored_entity_id == interlocutor_id
        assert len(req.revealed_fact_ids) == 5
        assert len(req.active_conditional_fact_ids) == 3
        assert req.participant_names[participant_1_id] == "Alice"
        assert req.recent_window_turns == 8
        assert req.recall_budget_tokens == 3000
        assert req.last_actor_utterance == "Tell me more."


class TestMemoryItem:
    def test_valid_memory_item(self) -> None:
        item = MemoryItem(
            kind="span",
            item_id=uuid4(),
            source_kind="turn_narration",
            authority="extracted",
            assertion="occurred",
            sequence=15,
            speaker="Narrator",
            text="A dragon appeared.",
            entity_ids=[uuid4(), uuid4()],
            branches=["exact", "vector"],
        )
        assert item.kind == "span"
        assert item.speaker == "Narrator"
        assert len(item.branches) == 2

    def test_memory_item_no_assertion(self) -> None:
        item = MemoryItem(
            kind="fact",
            item_id=uuid4(),
            source_kind="authored_lore",
            authority="authored",
            assertion=None,
            sequence=0,
            speaker=None,
            text="A fact about the world.",
            entity_ids=[],
            branches=["graph"],
        )
        assert item.assertion is None


class TestActiveEntity:
    def test_valid_active_entity_authored(self) -> None:
        entity = ActiveEntity(
            entity_id=uuid4(),
            authored_entity_id=uuid4(),
            name="Dragon",
            provenance="authored",
        )
        assert entity.provenance == "authored"
        assert entity.brief is None

    def test_valid_active_entity_extracted_with_brief(self) -> None:
        entity = ActiveEntity(
            entity_id=uuid4(),
            authored_entity_id=None,
            name="Stranger",
            provenance="extracted",
            brief="A mysterious figure",
        )
        assert entity.provenance == "extracted"
        assert entity.brief == "A mysterious figure"


class TestSceneAtSequence:
    def test_valid_scene(self) -> None:
        scene = SceneAtSequence(
            valid_from_seq=5,
            location_entity_id=uuid4(),
            present_entity_ids=[uuid4(), uuid4()],
        )
        assert scene.valid_from_seq == 5
        assert len(scene.present_entity_ids) == 2

    def test_scene_no_location(self) -> None:
        scene = SceneAtSequence(
            valid_from_seq=0,
            location_entity_id=None,
            present_entity_ids=[],
        )
        assert scene.location_entity_id is None


class TestWatermarks:
    def test_valid_watermarks(self) -> None:
        wm = Watermarks(
            ingested_seq=20,
            indexed_seq=18,
            extracted_seq=15,
            latest_seq_seen=22,
        )
        assert wm.ingested_seq == 20
        assert wm.indexed_seq == 18
        assert wm.extracted_seq == 15
        assert wm.latest_seq_seen == 22


class TestRetrieveResponse:
    def test_valid_response_minimal(self) -> None:
        item = MemoryItem(
            kind="span",
            item_id=uuid4(),
            source_kind="turn_narration",
            authority="extracted",
            assertion="occurred",
            sequence=10,
            speaker="Narrator",
            text="Something happened.",
            entity_ids=[],
            branches=["bm25"],
        )
        scene = SceneAtSequence(
            valid_from_seq=8,
            location_entity_id=uuid4(),
            present_entity_ids=[uuid4()],
        )
        wm = Watermarks(
            ingested_seq=12,
            indexed_seq=11,
            extracted_seq=10,
            latest_seq_seen=12,
        )

        resp = RetrieveResponse(
            items=[item],
            active_entities=[],
            scene=scene,
            watermarks=wm,
            degraded_reasons=[],
            embedding_model="text-embedding-005",
        )
        assert len(resp.items) == 1
        assert resp.skipped_branches == []

    def test_valid_response_with_skipped_branches(self) -> None:
        wm = Watermarks(
            ingested_seq=10,
            indexed_seq=9,
            extracted_seq=8,
            latest_seq_seen=10,
        )
        resp = RetrieveResponse(
            items=[],
            active_entities=[],
            scene=None,
            watermarks=wm,
            degraded_reasons=["indexing_lag"],
            embedding_model="text-embedding-005",
            skipped_branches=["vector", "bm25"],
        )
        assert resp.skipped_branches == ["vector", "bm25"]
        assert "indexing_lag" in resp.degraded_reasons


class TestExtractionContext:
    def test_valid_extraction_context(self) -> None:
        ctx = ExtractionContext(
            lines=["Line 1", "Line 2", "Line 3"],
            entity_ids=[uuid4(), uuid4()],
            token_count=150,
            truncated=False,
        )
        assert len(ctx.lines) == 3
        assert len(ctx.entity_ids) == 2
        assert ctx.token_count == 150
        assert ctx.truncated is False

    def test_extraction_context_truncated(self) -> None:
        ctx = ExtractionContext(
            lines=["Line 1"],
            entity_ids=[],
            token_count=3000,
            truncated=True,
        )
        assert ctx.truncated is True
