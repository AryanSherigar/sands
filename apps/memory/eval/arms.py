"""Scores one probe for the baseline arm (memory off) and the memory arm."""

import math

from app.models.retrieve import RetrieveResponse

from eval.baseline_text import CHARS_PER_TOKEN, InlineText
from eval.corpus_models import PlantDef, ProbeDef
from eval.run_models import ProbeRecord
from eval.scoring.retrieval import (
    Chunk,
    ProbeScore,
    ResolvedProbe,
    resolve_probe,
    score_probe,
)

BASELINE_ARM = "baseline"
MEMORY_ARM = "memory"


def chunks_from_response(response: RetrieveResponse) -> list[Chunk]:
    return [
        Chunk(
            item.text, math.ceil(len(item.text) / CHARS_PER_TOKEN), tuple(item.branches)
        )
        for item in response.items
    ]


def _visible(inline: InlineText, recalled: list[Chunk]) -> str:
    return "\n\n".join([inline.window_text, *(chunk.text for chunk in recalled)])


def _record(
    score: ProbeScore,
    arm: str,
    style: str,
    retrieve_ms: float | None,
    response: RetrieveResponse | None,
) -> ProbeRecord:
    return ProbeRecord(
        probe_id=score.probe_id,
        failure_class=score.failure_class,
        arm=arm,
        required_total=score.required_total,
        required_found=score.required_found,
        forbidden_count=score.forbidden_count,
        stale_span_count=score.stale_span_count,
        distractor_count=score.distractor_count,
        style=style,
        irrelevant_token_share=score.irrelevant_token_share,
        recalled_tokens=score.recalled_tokens,
        hit_at=score.hit_at,
        reciprocal_rank=score.reciprocal_rank,
        ndcg=score.ndcg,
        branch_hits=dict(score.branch_hits),
        graph_only_found=score.is_graph_only_found,
        retrieve_ms=retrieve_ms,
        degraded_reasons=list(response.degraded_reasons) if response else [],
        skipped_branches=list(response.skipped_branches) if response else [],
    )


def score_both_arms(
    probe: ProbeDef,
    plants: dict[str, PlantDef],
    inline: InlineText,
    response: RetrieveResponse,
    retrieve_ms: float,
    names: dict[str, str],
) -> list[ProbeRecord]:
    resolved: ResolvedProbe = resolve_probe(probe, plants, names)
    memory_chunks = chunks_from_response(response)
    memory = score_probe(resolved, _visible(inline, memory_chunks), memory_chunks)
    baseline = score_probe(
        resolved, _visible(inline, inline.lore_chunks), inline.lore_chunks
    )
    return [
        _record(baseline, BASELINE_ARM, probe.style, None, None),
        _record(memory, MEMORY_ARM, probe.style, retrieve_ms, response),
    ]
