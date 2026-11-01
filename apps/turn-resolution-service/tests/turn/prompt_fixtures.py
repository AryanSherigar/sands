"""Two consecutive turns of fixed narration and assistant inputs.

Data only, no rendering: the golden-prompt capture and the prefix-stability tests
render these through the code under test. Turn 2 differs from turn 1 in every
per-turn input (state, location, on-scene entities, memory, history, directives,
action) and in nothing that belongs to the scenario or the playthrough.
"""

import copy
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.models.assistant import (
    AssistantChatMessage,
    AssistantChatRequest,
    AssistantDraftContext,
    AssistantEntitySummary,
    AssistantMasterContext,
    AssistantScopedContext,
    AssistantStoryCard,
)
from app.models.memory import (
    ActiveEntity,
    MemoryContext,
    MemoryItem,
    RetrieveResponse,
    SceneAtSequence,
    Watermarks,
)
from app.models.turn import LoadedState, RecentTurn, TurnContext, TurnRequest

NIGHT_DESK_FIXTURE = Path(__file__).parent / "fixtures" / "night_desk_export.json"
NAMESPACE = uuid.UUID("00000000-0000-0000-0000-00000000f1e7")
PLAYTHROUGH_ID = uuid.uuid5(NAMESPACE, "playthrough")
PARTICIPANT_ID = uuid.uuid5(NAMESPACE, "participant")
NEWBIE_SCENARIO_ID = uuid.uuid5(NAMESPACE, "newbie-scenario")
NIGHT_DESK_SCENARIO_ID = uuid.uuid5(NAMESPACE, "night-desk-scenario")
LOCATION_DESK = "9e52bdb0-bec0-5e39-a5d0-00ff000d9c66"
LOCATION_LOBBY = "4ad6e293-48f3-5342-9e7c-06711b7fff0d"
ENTITY_EVA = "5ac32761"
ENTITY_TALLIS = "7991ccd2"
ALWAYS_REMEMBER = ["The lamp must stay lit.", "Mara never lies."]
SCENARIO_PREMISE = "A keeper guards a failing light through one long storm."
SCENARIO_MOOD_TAGS = ["eerie", "tense"]
NARRATOR_INSTRUCTION = "Speak in clipped, clerical sentences; never raise your voice."


@dataclass(frozen=True)
class NarrationInputs:
    request: TurnRequest
    loaded_state: LoadedState
    context: TurnContext
    active_instructions: list[str]


def _watermarks() -> Watermarks:
    return Watermarks(ingested_seq=0, indexed_seq=0, extracted_seq=0, latest_seq_seen=0)


def _item(label: str, sequence: int) -> MemoryItem:
    return MemoryItem(
        kind="fact",
        item_id=uuid.uuid5(NAMESPACE, label),
        source_kind="fact",
        authority="authored",
        assertion="occurred",
        sequence=sequence,
        speaker=None,
        text=label,
        entity_ids=[],
    )


def _context(
    facts: list[str], turns: list[RecentTurn], active: list[ActiveEntity]
) -> TurnContext:
    response = RetrieveResponse(
        items=[_item(fact, index) for index, fact in enumerate(facts)],
        active_entities=active,
        scene=SceneAtSequence(
            valid_from_seq=0, location_entity_id=None, present_entity_ids=[]
        ),
        watermarks=_watermarks(),
        embedding_model="fixture",
    )
    return TurnContext(
        memory=MemoryContext(response=response),
        recent_turns=turns,
        participant_names={PARTICIPANT_ID: "Alex"},
    )


def _turns(count: int) -> list[RecentTurn]:
    return [
        RecentTurn(
            turn_number=number,
            participant_id=PARTICIPANT_ID,
            action_mode="do",
            action_text=f"I check item {number}.",
            narration_text=f"The room answers item {number} with a long silence.",
        )
        for number in range(1, count + 1)
    ]


def _request(action_text: str, turn_count: int) -> TurnRequest:
    return TurnRequest(
        playthrough_id=PLAYTHROUGH_ID,
        participant_id=PARTICIPANT_ID,
        client_action_id=uuid.uuid5(NAMESPACE, f"action-{turn_count}"),
        action_text=action_text,
        action_mode="do",
        turn_count=turn_count,
    )


def _full_entity_id(snapshot: dict[str, object], prefix: str) -> str:
    entities = snapshot["entities"]
    assert isinstance(entities, list)
    return next(
        str(entity["entity_id"])
        for entity in entities
        if str(entity["entity_id"]).startswith(prefix)
    )


def night_desk_turns() -> tuple[NarrationInputs, NarrationInputs]:
    """Night Desk with creator narrator instructions added to two entities, so the
    per-turn directive path is exercised."""
    export = json.loads(NIGHT_DESK_FIXTURE.read_text(encoding="utf-8"))
    snapshot = copy.deepcopy(export["snapshot"])
    snapshot["mood_tags"] = list(SCENARIO_MOOD_TAGS)
    snapshot.setdefault("world_data", {}).update(
        {"premise": SCENARIO_PREMISE, "alwaysRemember": list(ALWAYS_REMEMBER)}
    )
    for entity in snapshot["entities"]:
        if str(entity["entity_id"]).startswith((ENTITY_EVA, ENTITY_TALLIS)):
            entity["narrator_instruction"] = NARRATOR_INSTRUCTION
    eva = _full_entity_id(snapshot, ENTITY_EVA)
    tallis = _full_entity_id(snapshot, ENTITY_TALLIS)
    first_state = copy.deepcopy(export["initial_state"])
    first_state["count"]["wrong_entries"] = 1
    first_state["flags"]["greeter"] = eva
    second_state = copy.deepcopy(first_state)
    second_state["current_location_id"] = LOCATION_LOBBY
    second_state["count"]["wrong_entries"] = 2
    second_state["flags"]["greeter"] = tallis
    first = NarrationInputs(
        _request("I read the board by the door.", 3),
        _loaded(NIGHT_DESK_SCENARIO_ID, snapshot, first_state, 3),
        _context(["The lamp has never gone out."], _turns(3), []),
        [],
    )
    second = NarrationInputs(
        _request("I ask who closes the cabin.", 4),
        _loaded(NIGHT_DESK_SCENARIO_ID, snapshot, second_state, 4),
        _context(["Floor nine closes at eleven."], _turns(4), []),
        ["The lamp flickers; let dread build without naming the cause."],
    )
    return first, second


def _loaded(
    scenario_id: uuid.UUID,
    snapshot: dict[str, object],
    state: dict[str, object],
    turn_count: int,
) -> LoadedState:
    return LoadedState(
        scenario_id=scenario_id,
        scenario_snapshot=snapshot,
        state=state,
        turn_count=turn_count,
        checkpoint=None,
    )


def _newbie_snapshot() -> dict[str, object]:
    return {
        "mode": "newbie",
        "narrator_persona": "A weary lighthouse keeper who speaks in tide metaphors.",
        "entities": [
            {
                "entity_id": "player-entity",
                "canonical_name": "The Wanderer",
                "aliases": ["The Wanderer"],
                "description": "An exile with a salt-stained coat.",
                "is_player": True,
            }
        ],
        "mood_tags": list(SCENARIO_MOOD_TAGS),
        "opening_scene": "Rain hammers the glass as the keeper hands you the key.",
        "world_data": {
            "premise": SCENARIO_PREMISE,
            "alwaysRemember": list(ALWAYS_REMEMBER),
            "mainConflict": "The lamp must stay lit until the storm breaks.",
            "openingPrompt": "Rain hammers the glass as the keeper hands you the key.",
            "worldLore": "The coast is old.\n\nShips avoid the reef after dark.",
            "storyCards": [],
        },
    }


def newbie_turns() -> tuple[NarrationInputs, NarrationInputs]:
    snapshot = _newbie_snapshot()
    state: dict[str, object] = {
        "setup": {"character_name": "Kaelen"},
        "narrative": {
            "opening_prompt": "Rain hammers the glass; Kaelen takes the key."
        },
    }
    first = NarrationInputs(
        _request("I climb the stairs.", 2),
        _loaded(NEWBIE_SCENARIO_ID, snapshot, state, 2),
        _context(["The reef claims a ship each winter."], _turns(2), []),
        [],
    )
    second = NarrationInputs(
        _request("I trim the wick.", 3),
        _loaded(NEWBIE_SCENARIO_ID, snapshot, state, 3),
        _context(["The keeper's logbook is missing a page."], _turns(3), []),
        [],
    )
    return first, second


def assistant_requests() -> dict[
    str, tuple[AssistantChatRequest, AssistantChatRequest]
]:
    """A newbie and a master Studio request, each as the first message and then the
    same conversation after the creator edited the draft and changed section."""
    cards = [AssistantStoryCard(type="Faction", name="Silver Dawn", content="Knights")]
    draft = AssistantDraftContext(
        title="Chronicles of Elyria",
        genre_tags=["Dark Fantasy"],
        world_lore="Ancient dragons ruled the sky.",
        story_cards=cards,
        active_section="lore",
    )
    edited = draft.model_copy(
        update={"world_lore": "Dragons fell.", "active_section": "cards"}
    )
    master = AssistantMasterContext(
        title="Sunken Kingdom",
        entities=[
            AssistantEntitySummary(
                entity_id="entity-1", entity_type="character", canonical_name="Hero"
            )
        ],
    )
    master_edited = master.model_copy(update={"active_tab": "facts"})
    first_message = [AssistantChatMessage(role="user", content="Help me start.")]
    second_message = [
        *first_message,
        AssistantChatMessage(role="assistant", content="Sure."),
        AssistantChatMessage(role="user", content="Add a rival."),
    ]
    scoped = AssistantScopedContext(
        one_line_idea="A keeper guards a failing light.",
        tab_kind="premise",
        tab_label="Premise",
        tab_text="The storm is coming.",
    )
    scoped_edited = scoped.model_copy(
        update={
            "tab_kind": "always_remember",
            "tab_label": "Always remember",
            "tab_text": "The lamp must stay lit.",
        }
    )
    return {
        "scoped": (
            AssistantChatRequest(
                messages=first_message, mode="scoped", scoped_context=scoped
            ),
            AssistantChatRequest(
                messages=second_message, mode="scoped", scoped_context=scoped_edited
            ),
        ),
        "newbie": (
            AssistantChatRequest(messages=first_message, draft_context=draft),
            AssistantChatRequest(messages=second_message, draft_context=edited),
        ),
        "master": (
            AssistantChatRequest(
                messages=first_message, mode="master", master_context=master
            ),
            AssistantChatRequest(
                messages=second_message, mode="master", master_context=master_edited
            ),
        ),
    }
