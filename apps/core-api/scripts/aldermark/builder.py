"""Builds the Aldermark strategy scenario row from its traced map document."""

import json

from app.models.scenario import ScenarioCreate
from app.services.scenario_documents import apply_rendered_documents
from scripts.aldermark.map_assets import ASSETS_DIRECTORY
from strategy_contracts.publish_checks import check_publishable
from strategy_contracts.scenario import StrategyScenario

DOCUMENT_PATH = ASSETS_DIRECTORY / "scenario.json"
TITLE = "The Aldermark"
LOGLINE = (
    "Hold the crown of a fractured medieval realm against four rival houses "
    "through war, diplomacy and betrayal."
)
PLAYTIME = "2 to 3 hours"
GENRE_TAGS = ["Medieval Strategy", "Political Intrigue"]
CONTENT_TAG = "teen"
CONTENT_TAGS = ["political-intrigue"]


class AldermarkNotPublishableError(Exception):
    """The strategy document would be refused by the publish checks."""


def load_strategy_document(map_image_url: str) -> dict[str, object]:
    """The traced document with its map pointing at the stored image."""
    document: dict[str, object] = json.loads(DOCUMENT_PATH.read_text())
    document["map"] = {**document["map"], "image_url": map_image_url}  # type: ignore[dict-item]
    return document


def ensure_publishable(document: dict[str, object]) -> None:
    report = check_publishable(StrategyScenario.model_validate(document))
    if report.is_publishable:
        return
    messages = "; ".join(issue.message for issue in report.blocking)
    raise AldermarkNotPublishableError(messages)


def scenario_columns(map_image_url: str) -> dict[str, object]:
    document = load_strategy_document(map_image_url)
    ensure_publishable(document)
    payload = ScenarioCreate(
        title=TITLE,
        mode="strategy",
        complexity_tier="master",
        visibility="public",
        logline=LOGLINE,
        player_count_support="solo",
        estimated_playtime=PLAYTIME,
        cover_image_url=map_image_url,
        content_tag=CONTENT_TAG,
        content_tags=CONTENT_TAGS,
        genre_tags=GENRE_TAGS,
        strategy_document=document,
    )
    columns = payload.model_dump()
    apply_rendered_documents(columns)
    return columns
