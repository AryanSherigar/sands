"""Freezes a validated corpus: `python -m eval.freeze --version 2`. A frozen corpus never changes silently."""

import json
import sys
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from eval.corpus_loader import Campaign, load_campaign
from eval.corpus_validate import validate_campaign, validate_class_minimums
from eval.errors import HarnessError

FREEZE_FILE = "FREEZE.json"
VERSION_FILE = "VERSION"


class FreezeRecord(BaseModel):
    version: str
    frozen_on: str
    content_hashes: dict[str, str]
    probe_counts: dict[str, int]


def _campaigns(corpus_root: Path) -> list[Campaign]:
    return [load_campaign(p) for p in sorted(corpus_root.iterdir()) if p.is_dir()]


def write_freeze(corpus_root: Path, version: str) -> FreezeRecord:
    campaigns = _campaigns(corpus_root)
    errors = [e for c in campaigns for e in validate_campaign(c)]
    errors += validate_class_minimums(campaigns)
    if errors:
        raise HarnessError(
            "Refusing to freeze an invalid corpus:\n" + "\n".join(errors)
        )
    record = FreezeRecord(
        version=version,
        frozen_on=date.today().isoformat(),
        content_hashes={c.campaign_id: c.content_hash for c in campaigns},
        probe_counts={c.campaign_id: len(c.probes) for c in campaigns},
    )
    (corpus_root / VERSION_FILE).write_text(version + "\n", encoding="utf-8")
    (corpus_root / FREEZE_FILE).write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return record


def check_frozen(corpus_root: Path, campaigns: list[Campaign]) -> None:
    """No freeze file means nothing is frozen yet; a mismatch means the corpus was edited after it."""
    path = corpus_root / FREEZE_FILE
    if not path.is_file():
        return
    record = FreezeRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
    changed = [
        c.campaign_id
        for c in campaigns
        if record.content_hashes.get(c.campaign_id) != c.content_hash
    ]
    if changed:
        raise HarnessError(
            f"Campaigns {changed} changed after the version {record.version} freeze; "
            "bump the version with `python -m eval.freeze` or pass --allow-unfrozen"
        )


if __name__ == "__main__":
    version = sys.argv[sys.argv.index("--version") + 1]
    print(write_freeze(Path("eval/corpus"), version).model_dump_json(indent=2))
