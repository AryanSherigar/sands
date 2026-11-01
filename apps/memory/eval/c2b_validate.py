"""CLI: `python -m eval.c2b_validate --rewrites a.json b.json [--write]` or `--check`."""

import argparse
import json
from pathlib import Path

from eval.corpus_loader import Campaign, load_campaign
from eval.heldout import (
    C2B_FILE,
    build_probes,
    load_dropped,
    load_probes,
    validate_set,
    write_dropped,
    write_probes,
)

C2_DIRECTORY = Path(__file__).parent / "corpus" / "C2"


def read_rewrites(paths: list[Path]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in paths:
        merged.update(json.loads(path.read_text(encoding="utf-8")))
    return merged


def check_rewrites(
    campaign: Campaign, rewrites: dict[str, str], dropped: frozenset[str]
) -> list[str]:
    kept = {pid: text for pid, text in rewrites.items() if pid not in dropped}
    return validate_set(campaign, build_probes(campaign, kept), dropped)


def failing_probe_ids(errors: list[str]) -> list[str]:
    ids = {error.split(":", 1)[0].removesuffix("-b") for error in errors}
    return sorted(ids)


DROP_REASON = "failed the overlap cap or the no-hinting rule in 3 tries"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rewrites", nargs="*", type=Path, default=[])
    parser.add_argument("--drop", nargs="*", default=[])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    campaign = load_campaign(C2_DIRECTORY)
    dropped = frozenset(args.drop) or frozenset(load_dropped())
    if args.check:
        errors = validate_set(campaign, load_probes(C2B_FILE), dropped)
    else:
        errors = check_rewrites(campaign, read_rewrites(args.rewrites), dropped)
    for error in errors:
        print(error)
    print(f"failing probes: {failing_probe_ids(errors)}; dropped: {sorted(dropped)}")
    if args.write and not errors:
        kept = {
            k: v for k, v in read_rewrites(args.rewrites).items() if k not in dropped
        }
        write_probes(build_probes(campaign, kept))
        write_dropped({pid: DROP_REASON for pid in sorted(dropped)})
        print(f"wrote {C2B_FILE} with {len(kept)} probes")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
