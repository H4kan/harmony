from dataclasses import dataclass
from typing import Tuple
from core.melody import Melody
from core.stats import MelodyStats


class Filter:
    name: str

    def check(self, melody: Melody, stats: MelodyStats) -> Tuple[bool, str]:
        raise NotImplementedError


@dataclass(frozen=True)
class MaxStepFilter(Filter):
    name: str = "MaxStepFilter"
    max_abs_step: int = 7

    def check(self, melody: Melody, stats: MelodyStats):
        if max(stats.abs_intervals) > self.max_abs_step:
            return False, "step too large"
        return True, ""


@dataclass(frozen=True)
class AmbitusFilter(Filter):
    name: str = "AmbitusFilter"
    max_ambitus: int = 14

    def check(self, melody: Melody, stats: MelodyStats):
        if stats.ambitus > self.max_ambitus:
            return False, "ambitus too wide"
        return True, ""


@dataclass(frozen=True)
class TurnsRateFilter(Filter):
    name: str = "TurnsRateFilter"
    max_rate: float = 0.40

    def check(self, melody: Melody, stats: MelodyStats):
        rate = stats.turns / max(1, stats.n - 2)
        if rate > self.max_rate:
            return False, "too many direction changes"
        return True, ""


@dataclass(frozen=True)
class PitchClassConcentrationFilter(Filter):
    name: str = "PitchClassConcentrationFilter"
    min_top3_ratio: float = 0.40

    def check(self, melody: Melody, stats: MelodyStats):
        if stats.top3_ratio < self.min_top3_ratio:
            return False, "pitch classes too flat"
        return True, ""
