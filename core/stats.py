from dataclasses import dataclass
from typing import Tuple
from .melody import Melody


def _sgn(v: int) -> int:
    return 0 if v == 0 else (1 if v > 0 else -1)


@dataclass
class MelodyStats:
    n: int
    intervals: Tuple[int, ...]
    abs_intervals: Tuple[int, ...]
    turns: int
    ambitus: int
    pitch_class_hist: Tuple[int, ...]
    top1_ratio: float
    top3_ratio: float
    small_ratio: float
    large_ratio: float

    @staticmethod
    def compute(
        melody: Melody,
        *,
        modulo: int = 12,
        small_T: int = 4,
        large_L: int = 7,
    ) -> "MelodyStats":

        x = melody.pitches
        n = len(x)

        intervals = tuple(x[i + 1] - x[i] for i in range(n - 1))
        abs_intervals = tuple(abs(d) for d in intervals)

        # turns
        turns = 0
        prev = _sgn(intervals[0])
        for d in intervals[1:]:
            cur = _sgn(d)
            if cur != 0 and prev != 0 and cur != prev:
                turns += 1
            if cur != 0:
                prev = cur

        ambitus = max(x) - min(x)

        # pitch-class histogram
        hist = [0] * modulo
        for p in x:
            hist[p % modulo] += 1

        sorted_hist = sorted(hist, reverse=True)
        top1 = sorted_hist[0] / n
        top3 = sum(sorted_hist[:3]) / n

        small = sum(1 for a in abs_intervals if a <= small_T)
        large = sum(1 for a in abs_intervals if a >= large_L)

        return MelodyStats(
            n=n,
            intervals=intervals,
            abs_intervals=abs_intervals,
            turns=turns,
            ambitus=ambitus,
            pitch_class_hist=tuple(hist),
            top1_ratio=top1,
            top3_ratio=top3,
            small_ratio=small / (n - 1),
            large_ratio=large / (n - 1),
        )
