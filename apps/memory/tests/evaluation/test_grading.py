from eval import grading
from eval.corpus_models import ProbeDef


def make_probe(probe_id: str, failure_class: str = "long_range") -> ProbeDef:
    return ProbeDef(
        probe_id=probe_id,
        failure_class=failure_class,  # type: ignore[arg-type]
        at_turn=10,
        action_text="what is in his boot",
        action_mode="say",
        actor_key="p1",
        required=["r1"],
        forbidden_anchors=["a red feather"],
        expected_truth="a blue marble",
    )


def test_anchor_signals_find_required_and_forbidden_wording_ignoring_case_and_punctuation() -> (
    None
):
    probe = make_probe("a")
    text = "He pulls out a BLUE glass marble. Not a red feather!"
    signals = grading.anchor_signals(
        text, ["a blue glass marble", "a silver key"], probe
    )
    assert (signals.required_found, signals.required_total, signals.has_forbidden) == (
        1,
        2,
        True,
    )


def test_blind_batches_hide_the_arm_shuffle_deterministically_and_key_back() -> None:
    probes = {"a": make_probe("a"), "b": make_probe("b")}
    narrations = [
        grading.Narration(probe_id=pid, arm=arm, sample=n, text=f"story {pid} {n}")  # type: ignore[arg-type]
        for pid in probes
        for arm in ("baseline", "tuned")
        for n in (1, 2, 3)
    ]
    batches, key = grading.blind_batches(narrations, probes, {"a": ["x"]}, 5)
    again, _ = grading.blind_batches(narrations, probes, {"a": ["x"]}, 5)
    assert [len(b) for b in batches] == [5, 5, 2] and batches == again
    rendered = "".join(item.model_dump_json() for batch in batches for item in batch)
    assert "baseline" not in rendered and "tuned" not in rendered
    assert all("arm" not in item.model_dump() for batch in batches for item in batch)
    assert len(key) == 12 and {n.arm for n in key.values()} == {"baseline", "tuned"}


def test_agreement_statistics_on_known_cases() -> None:
    perfect = [
        ("correct", "correct"),
        ("incorrect", "incorrect"),
        ("not_addressed", "not_addressed"),
    ]
    assert (
        grading.raw_agreement(perfect) == 1.0 and grading.cohens_kappa(perfect) == 1.0
    )
    chance = [("correct", "incorrect"), ("incorrect", "correct")] * 5
    assert grading.raw_agreement(chance) == 0.0 and grading.cohens_kappa(chance) < 0
    mostly = (
        [("correct", "correct")] * 17
        + [("incorrect", "incorrect")] * 2
        + [("correct", "incorrect")]
    )
    assert grading.agreement_is_sufficient(mostly)
    lopsided = [("correct", "correct")] * 19 + [("correct", "incorrect")] * 1
    assert grading.raw_agreement(
        lopsided
    ) == 0.95 and not grading.agreement_is_sufficient(lopsided)


def test_audit_sample_is_class_balanced_after_a_calibration_set() -> None:
    classes = ["a", "b", "c", "d"]
    class_by_item = {f"i{n:04d}": classes[n % 4] for n in range(200)}
    calibration, stratified = grading.audit_sample(class_by_item, 40, 50)
    assert len(calibration) == 40 and len(stratified) == 50
    assert not set(calibration) & set(stratified)
    counts = {c: sum(1 for i in stratified if class_by_item[i] == c) for c in classes}
    assert max(counts.values()) - min(counts.values()) <= 1
