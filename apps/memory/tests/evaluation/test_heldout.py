from pathlib import Path

from eval import heldout
from eval.corpus_loader import load_campaign
from eval.corpus_models import ProbeDef

C2_DIRECTORY = Path(heldout.__file__).parent / "corpus" / "C2"


def c2_probe_with_anchor() -> tuple[ProbeDef, str]:
    campaign = load_campaign(C2_DIRECTORY)
    probe = next(p for p in campaign.probes if p.probe_id == "lr_1")
    return probe, heldout.anchor_texts(probe, campaign)[0]


def rewrite(probe: ProbeDef, text: str) -> ProbeDef:
    return heldout.with_rewritten_text(probe, text)


def test_overlap_share_counts_the_probe_content_words_found_in_the_anchor() -> None:
    share = heldout.overlap_share(
        "what does pip keep in his boot", "Pip keeps a marble in his boot"
    )
    assert 0.2 < share < 0.8
    assert heldout.overlap_share("hello there", "completely unrelated words") == 0.0
    assert heldout.overlap_share("", "anything") == 0.0


def test_a_shared_three_word_run_is_detected_in_either_casing_and_punctuation() -> None:
    assert heldout.shares_word_run(
        "He keeps a BLUE glass marble!", "Pip keeps a blue glass marble in his boot"
    )
    assert not heldout.shares_word_run(
        "what is in his boot", "Pip keeps a blue marble in his left boot"
    )


def test_the_original_wording_and_label_drift_are_rejected() -> None:
    campaign = load_campaign(C2_DIRECTORY)
    probe, _ = c2_probe_with_anchor()
    unchanged = heldout.validate_probe(
        rewrite(probe, probe.action_text), probe, campaign
    )
    assert any("unchanged" in error for error in unchanged)
    drifted = rewrite(probe, "wat's pip got hidden away").model_copy(
        update={"required": ["other"]}
    )
    assert any(
        "required differs" in error
        for error in heldout.validate_probe(drifted, probe, campaign)
    )


def test_a_loose_paraphrase_passes_and_a_close_copy_fails_the_overlap_cap() -> None:
    campaign = load_campaign(C2_DIRECTORY)
    probe, anchor = c2_probe_with_anchor()
    loose = rewrite(
        probe, "wait, anything weird on the little guy? thought he was hiding smth"
    )
    assert heldout.validate_probe(loose, probe, campaign) == []
    copy = rewrite(probe, anchor)
    errors = heldout.validate_probe(copy, probe, campaign)
    assert any("3-word run" in error for error in errors)
    assert any("overlap" in error for error in errors)


def test_vague_probes_are_exempt_from_the_word_share_cap_but_not_the_word_run_rule() -> (
    None
):
    campaign = load_campaign(C2_DIRECTORY)
    probe, anchor = c2_probe_with_anchor()
    vague = probe.model_copy(update={"style": "vague"})
    words = anchor.split()
    share_only = rewrite(vague, f"{words[0]} {words[-1]} {words[1]} it")
    errors = heldout.validate_probe(share_only, vague, campaign)
    assert not any("overlap" in error for error in errors)


def test_a_complete_set_covers_every_original_exactly_once() -> None:
    campaign = load_campaign(C2_DIRECTORY)
    rewrites = {p.probe_id: f"zzq {p.probe_id} qqz plz" for p in campaign.probes}
    probes = heldout.build_probes(campaign, rewrites)
    assert len(probes) == len(campaign.probes) == 64
    assert heldout.validate_set(campaign, probes) == []
    assert heldout.validate_set(campaign, probes[1:]) != []
    assert any(
        "duplicate" in e for e in heldout.validate_set(campaign, [*probes, probes[0]])
    )


def test_labels_of_a_built_probe_come_only_from_the_original() -> None:
    campaign = load_campaign(C2_DIRECTORY)
    original = campaign.probes[0]
    built = heldout.build_probes(
        campaign, {original.probe_id: "  totally new wording  "}
    )[0]
    assert (
        built.probe_id == f"{original.probe_id}-b"
        and built.action_text == "totally new wording"
    )
    assert (built.required, built.forbidden, built.failure_class) == (
        original.required,
        original.forbidden,
        original.failure_class,
    )


def test_freeze_records_the_probe_file_hash_and_count(tmp_path: Path) -> None:
    campaign = load_campaign(C2_DIRECTORY)
    probes = heldout.build_probes(
        campaign, {p.probe_id: f"rewrite {p.probe_id}" for p in campaign.probes[:3]}
    )
    path = tmp_path / "C2b.probes.jsonl"
    heldout.write_probes(probes, path)
    digest = heldout.write_freeze(path, tmp_path / "FREEZE.json")
    assert digest == heldout.probes_hash(path) and len(heldout.load_probes(path)) == 3
    assert '"probe_count": 3' in (tmp_path / "FREEZE.json").read_text(encoding="utf-8")


def test_failing_probe_ids_are_extracted_from_validation_errors() -> None:
    from eval.c2b_validate import failing_probe_ids

    errors = [
        "lr_1-b: shares a 3-word run with its anchor text",
        "mh_2: missing",
        "lr_1-b: x",
    ]
    assert failing_probe_ids(errors) == ["lr_1", "mh_2"]


def test_a_rewrite_may_not_introduce_evidence_words_except_entity_names() -> None:
    campaign = load_campaign(C2_DIRECTORY)
    original = next(p for p in campaign.probes if p.probe_id == "lr_6")
    leaky = heldout.with_rewritten_text(original, "didn't ketch lose some fingers")
    clean = heldout.with_rewritten_text(
        original, "what's up with ketch's hand, was he hurt back then"
    )
    assert heldout.introduced_words(leaky, original, campaign) == ["fingers"]
    assert heldout.introduced_words(clean, original, campaign) == []
    assert any(
        "introduces evidence words" in e
        for e in heldout.validate_probe(leaky, original, campaign)
    )


def test_dropped_probes_are_not_reported_missing_and_cannot_also_be_present(
    tmp_path: Path,
) -> None:
    campaign = load_campaign(C2_DIRECTORY)
    rewrites = {p.probe_id: f"zzq {p.probe_id} qqz plz" for p in campaign.probes}
    kept = {k: v for k, v in rewrites.items() if k != "lr_1"}
    probes = heldout.build_probes(campaign, kept)
    assert heldout.validate_set(campaign, probes) != []
    assert heldout.validate_set(campaign, probes, frozenset({"lr_1"})) == []
    heldout.write_dropped({"lr_1": "reason"}, tmp_path / "d.json")
    assert heldout.load_dropped(tmp_path / "d.json") == {"lr_1": "reason"}
