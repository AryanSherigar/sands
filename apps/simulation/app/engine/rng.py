import hashlib
from collections.abc import Sequence
from typing import TypeVar

MASK_64 = (1 << 64) - 1
RANGE_64 = 1 << 64
GOLDEN_GAMMA = 0x9E3779B97F4A7C15
MIX_MULTIPLIER_FIRST = 0xBF58476D1CE4E5B9
MIX_MULTIPLIER_SECOND = 0x94D049BB133111EB
MIX_SHIFT_FIRST = 30
MIX_SHIFT_SECOND = 27
MIX_SHIFT_FINAL = 31
STREAM_KEY_SEPARATOR = "\x1f"
STATE_BYTES = 8

StreamKey = str | int
ItemT = TypeVar("ItemT")


def derive_state(seed: int, *keys: StreamKey) -> int:
    parts = [str(seed), *(str(key) for key in keys)]
    digest = hashlib.sha256(STREAM_KEY_SEPARATOR.join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:STATE_BYTES], "big")


class DeterministicRng:
    def __init__(self, state: int, draw_count: int = 0) -> None:
        self._origin = state & MASK_64
        self._state = self._origin
        self._draw_count = draw_count

    @property
    def state(self) -> int:
        return self._state

    @property
    def draw_count(self) -> int:
        return self._draw_count

    def fork(self, *keys: StreamKey) -> "DeterministicRng":
        # NOTE: derived from the stream origin, not its position, so a fork is
        # identical no matter how many draws the parent has already made.
        return DeterministicRng(derive_state(self._origin, *keys))

    def next_u64(self) -> int:
        self._state = (self._state + GOLDEN_GAMMA) & MASK_64
        mixed = self._state
        mixed = ((mixed ^ (mixed >> MIX_SHIFT_FIRST)) * MIX_MULTIPLIER_FIRST) & MASK_64
        mixed = (
            (mixed ^ (mixed >> MIX_SHIFT_SECOND)) * MIX_MULTIPLIER_SECOND
        ) & MASK_64
        self._draw_count += 1
        return mixed ^ (mixed >> MIX_SHIFT_FINAL)

    def roll(self, upper: int) -> int:
        if upper < 1:
            raise ValueError("upper must be at least 1")
        accepted_limit = RANGE_64 - (RANGE_64 % upper)
        value = self.next_u64()
        while value >= accepted_limit:
            value = self.next_u64()
        return value % upper

    def roll_range(self, low: int, high: int) -> int:
        if high < low:
            raise ValueError("high must not be below low")
        return low + self.roll(high - low + 1)

    def shuffled(self, items: Sequence[ItemT]) -> list[ItemT]:
        result = list(items)
        for index in range(len(result) - 1, 0, -1):
            swap_index = self.roll(index + 1)
            result[index], result[swap_index] = result[swap_index], result[index]
        return result

    def weighted_choice(self, items: Sequence[ItemT], weights: Sequence[int]) -> ItemT:
        if not items or len(items) != len(weights) or min(weights) < 0:
            raise ValueError("items and non-negative weights must match")
        total = sum(weights)
        if total < 1:
            raise ValueError("at least one weight must be positive")
        ticket = self.roll(total)
        for item, weight in zip(items, weights, strict=True):
            if ticket < weight:
                return item
            ticket -= weight
        raise AssertionError("ticket always lands on an item")


def derive_rng(seed: int, turn: int, phase: str, *keys: StreamKey) -> DeterministicRng:
    return DeterministicRng(derive_state(seed, turn, phase, *keys))
