from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from core.melody import Melody
from core.stats import MelodyStats
from .filters import Filter
from .scorers import Scorer


@dataclass
class EvaluationResult:
    passed: bool
    score: float
    reason: str = ""
    filter_trace: List[Tuple[str, bool, str]] = field(default_factory=list)
    score_breakdown: List[Tuple[str, float]] = field(default_factory=list)
    stats: MelodyStats | None = None


@dataclass
class MelodyEvaluator:
    filters: List[Filter] = field(default_factory=list)
    scorers: List[Scorer] = field(default_factory=list)

    def evaluate(self, melody: Melody) -> EvaluationResult:
        stats = MelodyStats.compute(melody)

        trace: List[Tuple[str, bool, str]] = []
        for f in self.filters:
            ok, reason = f.check(melody, stats)
            trace.append((f.name, ok, reason))
            if not ok:
                return EvaluationResult(
                    passed=False,
                    score=float("-inf"),
                    reason=f"{f.name}: {reason}",
                    filter_trace=trace,
                    score_breakdown=[],
                    stats=stats,
                )

        breakdown: List[Tuple[str, float]] = []
        total = 0.0
        for s in self.scorers:
            v = s.score(melody, stats)
            breakdown.append((s.name, v))
            total += v

        return EvaluationResult(
            passed=True,
            score=total,
            reason="",
            filter_trace=trace,
            score_breakdown=breakdown,
            stats=stats,
        )
