import importlib.util
import re
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[4] / "scripts" / "live_budget.py"
ROW_PATTERN = re.compile(r"^\| \d{4}-\d{2}-\d{2} \| [\w.:-]+ \| \d+ \| \d+ \| \d+ \|$")


def _load_module():
    spec = importlib.util.spec_from_file_location("live_budget", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


live_budget = _load_module()


def _budget(tmp_path: Path, **overrides):
    values = {"max_input": 1_000, "max_output": 500} | overrides
    return live_budget.LiveBudget(tmp_path / "ledger.md", **values)


def _ledger_with(tmp_path: Path, input_tokens: int, output_tokens: int) -> Path:
    path = tmp_path / "ledger.md"
    live_budget.ensure_ledger(path)
    with path.open("a") as handle:
        handle.write(
            f"| 2026-10-30 | earlier | {input_tokens} | {output_tokens} | 0 |\n"
        )
    return path


def test_charge_raises_when_run_input_cap_reached(tmp_path: Path) -> None:
    budget = _budget(tmp_path)
    budget.charge(900, 10)
    with pytest.raises(live_budget.LiveBudgetExhausted):
        budget.charge(100, 0)


def test_charge_raises_when_run_output_cap_reached(tmp_path: Path) -> None:
    budget = _budget(tmp_path)
    with pytest.raises(live_budget.LiveBudgetExhausted):
        budget.charge(10, 500)


def test_would_exceed_uses_conservative_bound_before_a_call(tmp_path: Path) -> None:
    budget = _budget(tmp_path)
    budget.charge(600, 100)
    assert budget.would_exceed(input_bound=500, output_bound=10) is True
    assert budget.would_exceed(input_bound=300, output_bound=300) is False


def test_check_can_start_refuses_when_ledger_leaves_less_than_one_run_cap(
    tmp_path: Path,
) -> None:
    path = _ledger_with(tmp_path, 1_999_500, 0)
    budget = live_budget.LiveBudget(path, max_input=1_000, max_output=500)
    with pytest.raises(live_budget.LiveBudgetExhausted):
        budget.check_can_start()


def test_check_can_start_allows_a_run_with_enough_budget_left(
    tmp_path: Path,
) -> None:
    path = _ledger_with(tmp_path, 100_000, 50_000)
    live_budget.LiveBudget(path, max_input=1_000, max_output=500).check_can_start()


def test_override_allows_start_when_ledger_is_spent(tmp_path: Path) -> None:
    path = _ledger_with(tmp_path, 2_000_000, 2_000_000)
    budget = live_budget.LiveBudget(
        path, max_input=1_000, max_output=500, is_override=True
    )
    budget.check_can_start()


def test_record_run_appends_counts_only_row(tmp_path: Path) -> None:
    budget = _budget(tmp_path)
    budget.charge(10, 5, cached_tokens=3)

    budget.record_run("smoke | secret text\nsecond line")

    rows = [
        line
        for line in (tmp_path / "ledger.md").read_text().splitlines()
        if line.startswith("| 2")
    ]
    assert len(rows) == 1
    assert ROW_PATTERN.match(rows[0])
    assert rows[0].endswith("| 10 | 5 | 3 |")
    assert "secret" not in rows[0]


def test_from_env_defaults_to_250000(tmp_path: Path, monkeypatch) -> None:
    for name in (
        "LIVE_MAX_INPUT_TOKENS",
        "LIVE_MAX_OUTPUT_TOKENS",
        "LIVE_BUDGET_OVERRIDE",
    ):
        monkeypatch.delenv(name, raising=False)

    budget = live_budget.LiveBudget.from_env(tmp_path / "ledger.md")

    assert budget.max_input == 250_000
    assert budget.max_output == 250_000
    assert budget.is_override is False


def test_from_env_reads_overrides(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LIVE_MAX_INPUT_TOKENS", "30000")
    monkeypatch.setenv("LIVE_MAX_OUTPUT_TOKENS", "20000")
    monkeypatch.setenv("LIVE_BUDGET_OVERRIDE", "1")

    budget = live_budget.LiveBudget.from_env(tmp_path / "ledger.md")

    assert (budget.max_input, budget.max_output, budget.is_override) == (
        30_000,
        20_000,
        True,
    )
