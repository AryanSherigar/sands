from pathlib import Path

import pytest
from eval.errors import HarnessError, VariantCapError
from eval.variants import (
    MAX_TOTAL_VARIANTS,
    Variant,
    VariantRound,
    record_result,
    register_round,
    registered_count,
)
from pydantic import ValidationError


def make_round(
    round_id: str, count: int, env: dict[str, str] | None = None
) -> VariantRound:
    return VariantRound(
        round_id=round_id,
        family="extraction_prompt_validator",
        base=Variant(variant_id="base", description="carried forward", env=env or {}),
        variants=[
            Variant(variant_id=f"{round_id}-v{i}", description="x")
            for i in range(count)
        ],
    )


def test_effective_env_layers_the_variant_over_the_carried_forward_base() -> None:
    round_ = VariantRound(
        round_id="r1",
        family="extraction_model_shape",
        base=Variant(
            variant_id="base",
            description="b",
            env={
                "EXTRACTION_BATCH_TURNS": "5",
                "EXTRACTION_PROMPT_VERSION": "extraction_v1",
            },
        ),
        variants=[
            Variant(
                variant_id="batch10",
                description="d",
                env={"EXTRACTION_BATCH_TURNS": "10"},
            )
        ],
    )
    assert round_.effective_env(round_.variants[0]) == {
        "EXTRACTION_BATCH_TURNS": "10",
        "EXTRACTION_PROMPT_VERSION": "extraction_v1",
    }


@pytest.mark.parametrize(
    "name", ["NOT_A_SETTING", "MEMORY_DATABASE_URL", "EXTRACTION_API_KEY"]
)
def test_unknown_or_secret_settings_cannot_be_varied(name: str) -> None:
    with pytest.raises(ValidationError):
        Variant(variant_id="bad", description="d", env={name: "x"})


def test_a_round_rejects_duplicate_ids_a_bad_slug_and_too_many_variants() -> None:
    with pytest.raises(ValidationError):
        VariantRound(
            round_id="r",
            family="retrieval_levers",
            base=Variant(variant_id="a", description="d"),
            variants=[Variant(variant_id="a", description="d")],
        )
    with pytest.raises(ValidationError):
        Variant(variant_id="Bad Id", description="d")
    with pytest.raises(ValidationError):
        make_round("r", 5)


def test_registration_is_logged_once_and_counts_towards_the_cap(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    register_round(make_round("r1", 4), log)
    assert registered_count(log) == 4
    with pytest.raises(HarnessError):
        register_round(make_round("r1", 1), log)


def test_the_cap_refuses_a_round_that_would_pass_it(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    for index in range(MAX_TOTAL_VARIANTS // 4):
        register_round(make_round(f"r{index}", 4), log)
    with pytest.raises(VariantCapError):
        register_round(make_round("one-too-many", 1), log)
    assert registered_count(log) == MAX_TOTAL_VARIANTS


def test_results_are_logged_but_do_not_count_as_variants(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    register_round(make_round("r1", 2), log)
    record_result("r1", "r1-v0", ["run-a"], {"is_eligible": False}, log)
    assert registered_count(log) == 2
    assert "run-a" in log.read_text(encoding="utf-8")
