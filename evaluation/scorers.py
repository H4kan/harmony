from dataclasses import dataclass
from typing import Dict, Tuple
from core.melody import Melody
from core.stats import MelodyStats
import math

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


from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass(frozen=True)
class MotifNGramScorer(Scorer):
    name: str = "MotifNGramScorer"
    ngram: int = 4
    min_repeats: int = 2
    weight: float = 1.0

    # nowe parametry (sensowne defaulty)
    min_nonzero_in_ngram: int = 2   # wymuś “ruch” w motywie
    ignore_all_same: bool = True    # ignoruj (0,0,0,0), (-1,-1,-1,-1), (1,1,1,1)

    def score(self, melody: Melody, stats: MelodyStats) -> float:
        def sgn(v: int) -> int:
            return 0 if v == 0 else (1 if v > 0 else -1)

        contour = [sgn(d) for d in stats.intervals]
        counts: Dict[Tuple[int, ...], int] = {}

        for i in range(len(contour) - self.ngram + 1):
            g = tuple(contour[i:i + self.ngram])

            # 1) ignoruj n-gramy "wszystko takie samo"
            if self.ignore_all_same and len(set(g)) == 1:
                continue

            # 2) ignoruj n-gramy zbyt "płaskie" (za mało niezerowych)
            nonzero = sum(1 for x in g if x != 0)
            if nonzero < self.min_nonzero_in_ngram:
                continue

            counts[g] = counts.get(g, 0) + 1

        best = max(counts.values(), default=0)
        if best >= self.min_repeats:
            return self.weight * (best - self.min_repeats + 1)
        return 0.0


@dataclass(frozen=True)
class ClimaxPlacementScorer(Scorer):
    name: str = "ClimaxPlacementScorer"
    low: float = 0.45
    high: float = 0.85
    weight: float = 1.0

    def score(self, melody: Melody, stats: MelodyStats) -> float:
        pitches = melody.pitches
        mx = max(pitches)
        i = pitches.index(mx)  # pierwsze wystąpienie maksimum
        pos = i / (len(pitches) - 1)

        if pos < self.low:
            return self.weight * (-(self.low - pos) * 2.0)
        if pos > self.high:
            return self.weight * (-(pos - self.high) * 2.0)
        return self.weight * 1.0


@dataclass(frozen=True)
class EndNearStartScorer(Scorer):
    name: str = "EndNearStartScorer"
    tolerance: int = 2  # półtony
    weight: float = 0.8

    def score(self, melody: Melody, stats: MelodyStats) -> float:
        start = melody.pitches[0]
        end = melody.pitches[-1]
        dist = abs(end - start)
        if dist <= self.tolerance:
            return self.weight * 1.0
        return self.weight * (-(dist - self.tolerance) / 6.0)
    
@dataclass(frozen=True)
class TurnsTargetScorer(Scorer):
    name: str = "TurnsTargetScorer"
    target: float = 0.25   # 0.20–0.35 zwykle brzmi “melodyjnie”
    width: float = 0.12
    weight: float = 1.0

    def score(self, melody: Melody, stats: MelodyStats) -> float:
        denom = max(1, stats.n - 2)
        tr = stats.turns / denom
        x = (tr - self.target) / self.width
        return self.weight * (1.0 - x*x)


@dataclass(frozen=True)
class IntervalEntropyScorer(Scorer):
    name: str = "IntervalEntropyScorer"
    weight: float = 1.0
    target_bits: float = 2.2   # 2.0–2.6 sensowny zakres
    width: float = 1.0         # jak mocno kara odchylenia

    def score(self, melody: Melody, stats: MelodyStats) -> float:
        p = melody.pitches
        if len(p) < 2:
            return -1.0 * self.weight

        intervals = [p[i+1] - p[i] for i in range(len(p)-1)]

        counts = {}
        for d in intervals:
            counts[d] = counts.get(d, 0) + 1

        n = len(intervals)
        H = 0.0
        for c in counts.values():
            prob = c / n
            H -= prob * math.log2(prob)

        x = (H - self.target_bits) / self.width
        return self.weight * (1.0 - x * x)

@dataclass(frozen=True)
class PitchClassTop3TargetScorer(Scorer):
    name: str = "PitchClassTop3TargetScorer"
    target: float = 0.65
    width: float = 0.18
    weight: float = 0.8

    def score(self, melody: Melody, stats: MelodyStats) -> float:
        hist = stats.pitch_class_hist
        n = sum(hist)
        if n <= 0:
            return -1.0 * self.weight
        top3 = sum(sorted(hist, reverse=True)[:3])
        ratio = top3 / n
        x = (ratio - self.target) / self.width
        return self.weight * (1.0 - x*x)