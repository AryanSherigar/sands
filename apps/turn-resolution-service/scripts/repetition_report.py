"""Score how repetitive a finished run's narration is.

    python scripts/repetition_report.py narration.json

The file is a JSON list with one narration string per turn. Lower opener share and
higher novelty are better; the phrase list is what the narrator keeps reusing.
"""

import argparse
import json
from pathlib import Path

from app.turn.repetition import summarize


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("narration", type=Path)
    return parser.parse_args()


def main() -> None:
    turns: list[str] = json.loads(parse_args().narration.read_text(encoding="utf-8"))
    report = summarize(turns)
    print(f"turns={report.turns} average_words={report.average_words}")
    print(f"novelty={report.novelty} (1.0 = no reused three-word runs)")
    print(f"closing formula: {report.closing_share:.0%} of turns end alike")
    print(
        f"openers: '{report.most_common_opener}' starts "
        f"{report.opener_share:.0%} of turns"
    )
    for phrase, count in report.top_phrases:
        print(f"  {count:>2} turns  {phrase}")


if __name__ == "__main__":
    main()
