# evaluation/evaluator.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

from core.melody import Melody
from core.stats import MelodyStats
from core.io import SearchResult  # jeśli SearchResult jest gdzie indziej, popraw import


class MelodyEvaluator:
    def __init__(self, filters, scorers):
        self.filters = list(filters)
        self.scorers = list(scorers)

    def evaluate(self, melody: Melody) -> SearchResult:
        stats = MelodyStats.compute(melody)

        filter_trace: List[Dict[str, Any]] = []
        for flt in self.filters:
            passed, reason = flt.check(melody, stats)
            filter_trace.append({
                "type": flt.__class__.__name__,
                "passed": bool(passed),
                "reason": str(reason) if reason else "",
                "params": {k: v for k, v in flt.__dict__.items() if not k.startswith("_")},
            })
            if not passed:
                return SearchResult(
                    melody=melody,
                    score=float("-inf"),
                    passed=False,
                    reason=str(reason) if reason else flt.__class__.__name__,
                    score_breakdown=[],
                    filter_trace=filter_trace,
                    meta={"stats": _stats_to_meta(stats)},
                )

        score_breakdown: List[Dict[str, Any]] = []
        total = 0.0
        for scr in self.scorers:
            val = float(scr.score(melody, stats))
            total += val
            score_breakdown.append({
                "type": scr.__class__.__name__,
                "value": val,
                "params": {k: v for k, v in scr.__dict__.items() if not k.startswith("_")},
            })

        return SearchResult(
            melody=melody,
            score=total,
            passed=True,
            reason="",
            score_breakdown=score_breakdown,
            filter_trace=filter_trace,
            meta={"stats": _stats_to_meta(stats)},
        )


def _stats_to_meta(stats: MelodyStats) -> dict:
    # minimalnie użyteczne rzeczy do debugowania
    return {
        "n": stats.n,
        "ambitus": stats.ambitus,
        "turns": stats.turns,
        "pitch_class_hist": list(getattr(stats, "pitch_class_hist", [])),
        # jeśli stats.intervals istnieje:
        "intervals_head": list(getattr(stats, "intervals", [])[:16]),
    }
