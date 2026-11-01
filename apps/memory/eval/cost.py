"""Prints the cost split of a recorded run: `python -m eval.cost --report <report.json>`."""

import json
import sys
from pathlib import Path

from eval.prices import RunUsage, compute_cost, load_prices

USAGE_KEY = "usage"


def format_cost(usage: RunUsage) -> str:
    cost = compute_cost(usage, load_prices())
    lines = [
        f"extraction      ${cost.extraction_usd:.4f}",
        f"embeddings      ${cost.embedding_usd:.4f}",
        f"query embedding ${cost.query_embedding_usd:.4f}",
        f"total           ${cost.total_usd:.4f}",
    ]
    return "\n".join(lines)


def main(report_path: Path) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    print(format_cost(RunUsage.model_validate(report[USAGE_KEY])))


if __name__ == "__main__":
    main(Path(sys.argv[sys.argv.index("--report") + 1]))
