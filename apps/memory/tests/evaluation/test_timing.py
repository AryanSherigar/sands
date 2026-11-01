import json

from eval.timing import parse_stage_timings


def _line(event: str, stage_ms: dict[str, int]) -> str:
    return json.dumps({"event": event, "stage_ms": stage_ms, "level": "info"})


def test_stage_timings_average_per_stage_and_separate_retrieval_from_extraction() -> (
    None
):
    lines = [
        "INFO:     Started server process",
        _line("retrieve_completed", {"bm25": 10, "vector": 1000}),
        _line("retrieve_completed", {"bm25": 20, "vector": 3000, "pack": 4}),
        _line("extraction_batch_timed", {"llm": 2000, "apply": 40}),
        _line("embedding_batch", {"ignored": 1}),
        "{not json",
    ]
    timings = parse_stage_timings(lines)
    assert timings.retrieval_ms == {"bm25": 15.0, "pack": 4.0, "vector": 2000.0}
    assert timings.extraction_ms == {"apply": 40.0, "llm": 2000.0}


def test_an_empty_log_gives_empty_timings() -> None:
    timings = parse_stage_timings([])
    assert timings.retrieval_ms == {} and timings.extraction_ms == {}
