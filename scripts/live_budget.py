"""Token budget meter for the opt-in live Muse test suites.

Standard library only, so every service's live tests can load it by file path.
The ledger records counts and a sanitised label, never prompt or reply text.
"""

import os
import re
from datetime import date
from pathlib import Path

TOTAL_INPUT_TOKENS = 2_000_000
TOTAL_OUTPUT_TOKENS = 2_000_000
DEFAULT_RUN_CAP_TOKENS = 250_000
ENV_MAX_INPUT = "LIVE_MAX_INPUT_TOKENS"
ENV_MAX_OUTPUT = "LIVE_MAX_OUTPUT_TOKENS"
ENV_OVERRIDE = "LIVE_BUDGET_OVERRIDE"
LEDGER_HEADER = (
    "# Live Muse token ledger\n\n"
    "Counts only. Total budget: 2,000,000 input and 2,000,000 output tokens, "
    "shared by every live run.\n\n"
    "| date | label | input | output | cached |\n"
    "|---|---|---|---|---|\n"
)
ROW_PATTERN = re.compile(r"^\| \d{4}-\d{2}-\d{2} \| [^|]* \| (\d+) \| (\d+) \| \d+ \|$")
LABEL_UNSAFE = re.compile(r"[^\w.:-]+")
MAX_LABEL_CHARS = 40


class LiveBudgetExhausted(Exception):
    pass


def ensure_ledger(ledger_path: Path) -> None:
    if not ledger_path.exists():
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(LEDGER_HEADER)


def _spent_in_ledger(ledger_path: Path) -> tuple[int, int]:
    if not ledger_path.exists():
        return 0, 0
    spent_input = spent_output = 0
    for line in ledger_path.read_text().splitlines():
        match = ROW_PATTERN.match(line)
        if match:
            spent_input += int(match.group(1))
            spent_output += int(match.group(2))
    return spent_input, spent_output


def _clean_label(label: str) -> str:
    cleaned = LABEL_UNSAFE.sub("_", label.split("\n")[0].split("|")[0].strip())
    return cleaned[:MAX_LABEL_CHARS] or "run"


class LiveBudget:
    def __init__(
        self,
        ledger_path: Path,
        max_input: int,
        max_output: int,
        total_input: int = TOTAL_INPUT_TOKENS,
        total_output: int = TOTAL_OUTPUT_TOKENS,
        is_override: bool = False,
    ) -> None:
        self.ledger_path = ledger_path
        self.max_input = max_input
        self.max_output = max_output
        self.total_input = total_input
        self.total_output = total_output
        self.is_override = is_override
        self.used_input = 0
        self.used_output = 0
        self.used_cached = 0

    @classmethod
    def from_env(cls, ledger_path: Path) -> "LiveBudget":
        return cls(
            ledger_path,
            max_input=int(os.environ.get(ENV_MAX_INPUT, DEFAULT_RUN_CAP_TOKENS)),
            max_output=int(os.environ.get(ENV_MAX_OUTPUT, DEFAULT_RUN_CAP_TOKENS)),
            is_override=os.environ.get(ENV_OVERRIDE) == "1",
        )

    def check_can_start(self) -> None:
        if self.is_override:
            return
        spent_input, spent_output = _spent_in_ledger(self.ledger_path)
        has_input_left = self.total_input - spent_input >= self.max_input
        has_output_left = self.total_output - spent_output >= self.max_output
        if not (has_input_left and has_output_left):
            raise LiveBudgetExhausted("ledger leaves less than one run cap")

    def would_exceed(self, input_bound: int, output_bound: int) -> bool:
        return (
            self.used_input + input_bound > self.max_input
            or self.used_output + output_bound > self.max_output
        )

    def charge(
        self, input_tokens: int, output_tokens: int, cached_tokens: int = 0
    ) -> None:
        self.used_input += input_tokens
        self.used_output += output_tokens
        self.used_cached += cached_tokens
        if self.used_input >= self.max_input or self.used_output >= self.max_output:
            raise LiveBudgetExhausted("run token cap reached")

    def record_run(self, label: str) -> None:
        ensure_ledger(self.ledger_path)
        row = (
            f"| {date.today().isoformat()} | {_clean_label(label)} | "
            f"{self.used_input} | {self.used_output} | {self.used_cached} |\n"
        )
        with self.ledger_path.open("a") as handle:
            handle.write(row)
