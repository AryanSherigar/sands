import math
from collections import Counter

from eval.corpus_models import PlantDef, ProbeDef
from eval.scoring.retrieval import Chunk, resolve_probe, score_probe
from eval.scoring.stats import bootstrap_interval, summarize_by_class


def _plant(plant_id: str, anchor: str) -> PlantDef:
    return PlantDef(
        plant_id=plant_id, source="turn", turn=1, kind="fact", anchor_text=anchor
    )


def _probe(**overrides: object) -> ProbeDef:
    values: dict[str, object] = {
        "probe_id": "p",
        "failure_class": "long_range",
        "at_turn": 5,
        "action_text": "I ask.",
        "action_mode": "say",
        "actor_key": "p1",
        "required": ["a", "b"],
        "expected_truth": "x",
    }
    values.update(overrides)
    return ProbeDef.model_validate(values)


PLANTS = {
    "a": _plant("a", "alpha anchor"),
    "b": _plant("b", "beta anchor"),
    "old": _plant("old", "stale anchor"),
}


def _score(recalled: list[Chunk], visible: str = "", **probe: object):
    resolved = resolve_probe(_probe(**probe), PLANTS)
    return score_probe(
        resolved, visible + " ".join(chunk.text for chunk in recalled), recalled
    )


def test_recall_counts_required_anchors_visible_anywhere() -> None:
    score = _score([Chunk("has alpha anchor", 4)], visible="beta anchor in window ")
    assert score.recall == 1.0


def test_recall_is_partial_when_one_anchor_is_missing() -> None:
    score = _score([Chunk("has alpha anchor", 4)])
    assert score.required_found == 1 and score.recall == 0.5


def test_forbidden_counts_only_recalled_text() -> None:
    chunks = [Chunk("alpha anchor and stale anchor", 6)]
    score = _score(chunks, visible="stale anchor in window", forbidden=["old"])
    assert score.forbidden_count == 1
    clean = _score(
        [Chunk("alpha anchor", 3)], visible="stale anchor in window", forbidden=["old"]
    )
    assert clean.forbidden_count == 0


def test_forbidden_anchor_strings_are_checked() -> None:
    score = _score(
        [Chunk("Zephyrine Quill sails", 4)], forbidden_anchors=["Zephyrine Quill"]
    )
    assert score.forbidden_count == 1


def test_irrelevant_share_weights_by_tokens() -> None:
    chunks = [Chunk("alpha anchor", 10), Chunk("noise", 30)]
    assert _score(chunks).irrelevant_token_share == 0.75


def test_ranking_metrics_use_first_relevant_item() -> None:
    chunks = [Chunk("noise", 1), Chunk("noise", 1), Chunk("beta anchor", 1)]
    score = _score(chunks)
    assert score.hit_at == {1: 0.0, 3: 1.0, 5: 1.0}
    assert math.isclose(score.reciprocal_rank, 1 / 3)


def test_ndcg_is_one_for_ideal_order_and_lower_otherwise() -> None:
    ideal = _score([Chunk("alpha anchor", 1), Chunk("beta anchor", 1)])
    worse = _score(
        [Chunk("noise", 1), Chunk("alpha anchor", 1), Chunk("beta anchor", 1)]
    )
    assert math.isclose(ideal.ndcg, 1.0)
    assert worse.ndcg < 1.0


def test_branch_attribution_and_graph_only_count() -> None:
    chunks = [
        Chunk("alpha anchor", 1, ("graph",)),
        Chunk("beta anchor", 1, ("exact", "bm25")),
    ]
    score = _score(chunks)
    assert score.branch_hits == Counter({"graph": 1, "exact": 1, "bm25": 1})
    assert score.is_graph_only_found == 1


def test_empty_recall_scores_zero_without_dividing_by_zero() -> None:
    score = _score([])
    assert (
        score.recall == 0.0
        and score.irrelevant_token_share == 0.0
        and score.ndcg == 0.0
    )


def test_bootstrap_is_deterministic_and_brackets_the_mean() -> None:
    values = [0.0, 1.0, 1.0, 0.5, 0.75, 1.0]
    first, second = bootstrap_interval(values), bootstrap_interval(values)
    assert first == second and first is not None
    assert first.low <= first.mean <= first.high


def test_single_sample_has_no_interval() -> None:
    assert bootstrap_interval([1.0]) is None


def test_summary_groups_by_failure_class() -> None:
    scores = [
        _score([Chunk("alpha anchor beta anchor", 1)], failure_class="long_range")
        for _ in range(3)
    ]
    summary = summarize_by_class(scores, lambda score: score.recall)
    assert set(summary) == {"long_range"} and summary["long_range"] is not None


def test_state_only_classes_judge_state_items_and_report_stale_spans_separately() -> (
    None
):
    probe = {
        "failure_class": "knowledge_update",
        "required": ["a"],
        "forbidden": ["old"],
    }
    span = Chunk("alpha anchor then stale anchor", 5, kind="span")
    fact = Chunk("stale anchor", 3, kind="fact")
    in_span = _score([span], **probe)
    assert in_span.forbidden_count == 0 and in_span.stale_span_count == 1
    assert _score([span, fact], **probe).forbidden_count == 1


def test_distractors_are_counted_as_wrong_referents_not_forbidden_exposures() -> None:
    probe = {"required": ["a"], "distractors": ["old"]}
    chunk = Chunk("alpha anchor and stale anchor", 6)
    score = _score([chunk], **probe)
    assert score.distractor_count == 1 and score.forbidden_count == 0
    clean = _score([Chunk("alpha anchor", 3)], **probe)
    assert clean.distractor_count == 0


def test_ndcg_never_exceeds_one_when_a_plant_matches_several_items() -> None:
    chunks = [
        Chunk("alpha anchor", 1),
        Chunk("alpha anchor again", 1),
        Chunk("beta anchor", 1),
    ]
    score = _score(chunks)
    assert 0.0 < score.ndcg <= 1.0
    only_repeats = _score([Chunk("alpha anchor", 1)] * 5, required=["a"])
    assert only_repeats.ndcg <= 1.0


def test_recall_tokens_are_recorded_so_empty_recall_can_be_reported_as_n_a() -> None:
    assert _score([]).recalled_tokens == 0
    assert _score([Chunk("alpha anchor", 7)]).recalled_tokens == 7
