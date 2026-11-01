"""Asserts that two prompts share a byte-identical head, for implicit caching.

Vertex caches the longest prefix two requests have in common, so anything that
differs before a prompt's volatile tail costs the cache hit (ADR-21).
"""


def shared_prefix_length(first: str, second: str) -> int:
    length = 0
    for left, right in zip(first, second, strict=False):
        if left != right:
            break
        length += 1
    return length


def assert_shared_through(first: str, second: str, boundary: str) -> None:
    """Both texts hold `boundary`, at the same place, with identical text before it."""
    assert boundary in first, f"{boundary!r} missing from the first prompt"
    assert boundary in second, f"{boundary!r} missing from the second prompt"
    head = first.index(boundary)
    shared = shared_prefix_length(first, second)
    assert shared >= head, (
        f"prefix breaks at character {shared}, before {boundary!r} at {head}: "
        f"{first[max(shared - 40, 0) : shared + 40]!r} vs "
        f"{second[max(shared - 40, 0) : shared + 40]!r}"
    )
