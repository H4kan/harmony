from dataclasses import dataclass
from typing import Dict, Tuple
from core.melody import Melody
from core.stats import MelodyStats


class Scorer:
    name: str

    def score(self, melody: Melody, stats: MelodyStats) -> float:
        raise NotImplementedError


@dataclass(frozen=True)
class BellCurveIntervalScorer(Scorer):
    name: str = "BellCurveIntervalScorer"
    target: float = 2.5
    width: float = 1.2
    weight: float = 1.0

    def score(self, melody: Melody, stats: MelodyStats) -> float:
        mean_abs = sum(stats.abs_intervals) / len(stats.abs_intervals)
        z = (mean_abs - self.target) / self.width
        return self.weight * (-(z * z))


@dataclass(frozen=True)
class MotifNGramScorer(Scorer):
    name: str = "MotifNGramScorer"
    ngram: int = 4
    min_repeats: int = 2
    weight: float = 1.0

    def score(self, melody: Melody, stats: MelodyStats) -> float:
        def sgn(v: int) -> int:
            return 0 if v == 0 else (1 if v > 0 else -1)

        contour = [sgn(d) for d in stats.intervals]
        counts: Dict[Tuple[int, ...], int] = {}

        for i in range(len(contour) - self.ngram + 1):
            g = tuple(contour[i:i + self.ngram])
            counts[g] = counts.get(g, 0) + 1

        best = max(counts.values(), default=0)
        if best >= self.min_repeats:
            return self.weight * (best - self.min_repeats + 1)
        return 0.0
