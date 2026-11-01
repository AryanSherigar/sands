import json
from datetime import date
from pathlib import Path

from app.config import settings

from .scene_runner import ScenarioResult

REPORT_COLUMNS = "| scenario | exchanges | degraded | unparseable | input | output | cached | mean latency s |"
REPORT_RULE = "|---|---|---|---|---|---|---|---|"


def _row(result: ScenarioResult) -> str:
    exchanges = result.exchanges
    count = len(exchanges)
    latency = sum(item.latency_seconds for item in exchanges) / count if count else 0
    degraded = sum(item.was_degraded for item in exchanges)
    unparseable = sum(item.was_unparseable for item in exchanges)
    prompt = sum(item.usage.prompt_tokens for item in exchanges)
    completion = sum(item.usage.completion_tokens for item in exchanges)
    cached = sum(item.usage.cached_tokens for item in exchanges)
    return (
        f"| {result.scenario.name} | {count} | {degraded} | {unparseable} | "
        f"{prompt} | {completion} | {cached} | {latency:.1f} |"
    )


def write_report(results: list[ScenarioResult], path: Path) -> None:
    lines = [
        "# Live Muse scene harness results",
        "",
        f"Date: {date.today().isoformat()}. Model: {settings.openai_compatible_model_name}.",
        "Counts and timings only; no prompt or reply text.",
        "",
        REPORT_COLUMNS,
        REPORT_RULE,
        *[_row(result) for result in results],
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def write_decision_recording(results: list[ScenarioResult], path: Path) -> None:
    packages = {
        result.scenario.name: result.scenario.package.model_dump(mode="json")
        for result in results
    }
    decisions = [
        {
            "scenario": result.scenario.name,
            "scene_type": result.scenario.scene_type.value,
            "exchange_index": index,
            "decision": exchange.decision.model_dump(mode="json"),
        }
        for result in results
        for index, exchange in enumerate(result.exchanges)
        if exchange.decision is not None
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"packages": packages, "decisions": decisions}, indent=2)
    )
