"""C2b: user-style rewrites of the C2 probes, kept outside `corpus/` so C2's frozen hash is untouched."""

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path

from eval.corpus_loader import Campaign
from eval.corpus_models import ProbeDef

HELDOUT_DIRECTORY = Path(__file__).parent / "heldout"
C2B_FILE = HELDOUT_DIRECTORY / "C2b.probes.jsonl"
C2B_FREEZE_FILE = HELDOUT_DIRECTORY / "FREEZE.json"
C2B_DROPPED_FILE = HELDOUT_DIRECTORY / "C2b.dropped.json"
PROBE_ID_SUFFIX = "-b"
MAX_OVERLAP_SHARE = 0.30
MIN_CONTENT_WORD_LENGTH = 3
SHARED_RUN_WORDS = 3
MAX_TRIES = 3
MAX_ACTION_CHARACTERS = 300
TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
STOPWORDS = frozenset(
    [
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "have",
        "has",
        "had",
        "was",
        "were",
        "are",
        "not",
        "but",
        "you",
        "your",
        "his",
        "her",
        "its",
        "they",
        "them",
        "then",
        "than",
        "what",
        "when",
        "where",
        "who",
        "whom",
        "which",
        "will",
        "would",
        "could",
        "should",
        "into",
        "onto",
        "about",
        "over",
        "under",
        "again",
        "just",
        "can",
        "did",
        "does",
        "doing",
        "him",
        "she",
        "out",
        "off",
    ]
)
PARITY_FIELDS = (
    "failure_class",
    "at_turn",
    "actor_key",
    "action_mode",
    "required",
    "forbidden",
    "forbidden_anchors",
    "distractors",
    "style",
    "expected_truth",
)


def tokens_of(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def content_words(text: str) -> set[str]:
    return {
        word
        for word in tokens_of(text)
        if len(word) >= MIN_CONTENT_WORD_LENGTH and word not in STOPWORDS
    }


def overlap_share(probe_text: str, anchor_text: str) -> float:
    words = content_words(probe_text)
    return len(words & content_words(anchor_text)) / len(words) if words else 0.0


def _runs(text: str) -> set[tuple[str, ...]]:
    words = tokens_of(text)
    return {
        tuple(words[i : i + SHARED_RUN_WORDS])
        for i in range(len(words) - SHARED_RUN_WORDS + 1)
    }


def shares_word_run(probe_text: str, anchor_text: str) -> bool:
    return bool(_runs(probe_text) & _runs(anchor_text))


def anchor_texts(probe: ProbeDef, campaign: Campaign) -> list[str]:
    plants = {plant.plant_id: plant.anchor_text for plant in campaign.plants}
    return [plants[ref] for ref in probe.required if ref in plants]


def _text_errors(probe: ProbeDef, anchors: list[str]) -> list[str]:
    errors: list[str] = []
    if not probe.action_text.strip() or len(probe.action_text) > MAX_ACTION_CHARACTERS:
        errors.append("action text is empty or over the length limit")
    for anchor in anchors:
        if shares_word_run(probe.action_text, anchor):
            errors.append("shares a 3-word run with its anchor text")
        is_word_share_exempt = probe.style == "vague"
        if (
            not is_word_share_exempt
            and overlap_share(probe.action_text, anchor) > MAX_OVERLAP_SHARE
        ):
            errors.append(f"content-word overlap above {MAX_OVERLAP_SHARE:.0%}")
    return sorted(set(errors))


def entity_words(campaign: Campaign) -> set[str]:
    scenario = campaign.scenario
    names = [" ".join([e.canonical_name, *e.aliases]) for e in scenario.entities]
    names += [card.name for card in scenario.cards]
    return content_words(" ".join(names))


def introduced_words(
    probe: ProbeDef, original: ProbeDef, campaign: Campaign
) -> list[str]:
    """Evidence words the rewrite added that the original probe never used; names are exempt."""
    evidence = content_words(" ".join(anchor_texts(original, campaign)))
    added = content_words(probe.action_text) - content_words(original.action_text)
    return sorted((added & evidence) - entity_words(campaign))


def _parity_errors(probe: ProbeDef, original: ProbeDef) -> list[str]:
    errors = [
        f"{name} differs from {original.probe_id}"
        for name in PARITY_FIELDS
        if getattr(probe, name) != getattr(original, name)
    ]
    if probe.action_text.strip() == original.action_text.strip():
        errors.append("action text is unchanged from the original")
    return errors


def validate_probe(
    probe: ProbeDef, original: ProbeDef, campaign: Campaign
) -> list[str]:
    errors = _parity_errors(probe, original)
    errors += _text_errors(probe, anchor_texts(original, campaign))
    added = introduced_words(probe, original, campaign)
    if added:
        errors.append(f"introduces evidence words {added} the original did not use")
    return [f"{probe.probe_id}: {error}" for error in errors]


def validate_set(
    campaign: Campaign, probes: list[ProbeDef], dropped: frozenset[str] = frozenset()
) -> list[str]:
    originals = {probe.probe_id: probe for probe in campaign.probes}
    seen: set[str] = set()
    errors: list[str] = []
    for probe in probes:
        original = originals.get(probe.probe_id.removesuffix(PROBE_ID_SUFFIX))
        if original is None or probe.probe_id in seen:
            errors.append(f"{probe.probe_id}: unknown or duplicate probe id")
            continue
        seen.add(probe.probe_id)
        errors += validate_probe(probe, original, campaign)
    missing = sorted(
        f"{pid}{PROBE_ID_SUFFIX}" for pid in originals if pid not in dropped
    )
    errors += [f"{pid}: missing" for pid in missing if pid not in seen]
    return errors


def with_rewritten_text(original: ProbeDef, action_text: str) -> ProbeDef:
    return original.model_copy(
        update={
            "probe_id": f"{original.probe_id}{PROBE_ID_SUFFIX}",
            "action_text": action_text.strip(),
        }
    )


def build_probes(campaign: Campaign, rewrites: dict[str, str]) -> list[ProbeDef]:
    """Labels come only from the original probe; a rewrite supplies the wording and nothing else."""
    return [
        with_rewritten_text(probe, rewrites[probe.probe_id])
        for probe in campaign.probes
        if probe.probe_id in rewrites
    ]


def write_probes(probes: list[ProbeDef], path: Path = C2B_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [probe.model_dump_json() for probe in probes]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_dropped(path: Path = C2B_DROPPED_FILE) -> dict[str, str]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_dropped(reasons: dict[str, str], path: Path = C2B_DROPPED_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reasons, indent=2) + "\n", encoding="utf-8")


def load_probes(path: Path = C2B_FILE) -> list[ProbeDef]:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [ProbeDef.model_validate_json(line) for line in lines]


def probes_hash(path: Path = C2B_FILE) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def campaign_with_probes(campaign: Campaign, probes: list[ProbeDef]) -> Campaign:
    return replace(campaign, probes=probes)


def write_freeze(path: Path = C2B_FILE, freeze_path: Path = C2B_FREEZE_FILE) -> str:
    digest = probes_hash(path)
    record = {
        "probes_file": path.name,
        "sha256": digest,
        "probe_count": len(load_probes(path)),
    }
    freeze_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return digest
