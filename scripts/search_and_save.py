from __future__ import annotations

import time
from typing import Optional, Tuple

from core.io import SearchResult, save_result_json
from evaluation.filters import (
    MaxStepFilter,
    AmbitusFilter,
    TurnsRateFilter,
    PitchClassConcentrationFilter,
)
from evaluation.scorers import (
    BellCurveIntervalScorer,
    MotifNGramScorer,
)
from evaluation.evaluator import MelodyEvaluator
from generation.random_walk import random_walk


def main() -> None:
    evaluator = MelodyEvaluator(
        filters=[
            MaxStepFilter(max_abs_step=7),
            AmbitusFilter(max_ambitus=14),
            TurnsRateFilter(max_rate=0.40),
            PitchClassConcentrationFilter(min_top3_ratio=0.40),
        ],
        scorers=[
            BellCurveIntervalScorer(target=2.5, width=1.2, weight=1.0),
            MotifNGramScorer(ngram=4, min_repeats=2, weight=0.8),
        ],
    )

    best: Optional[Tuple[float, SearchResult]] = None
    tried = 20000
    n = 32

    for _ in range(tried):
        m = random_walk(n=n, start=60).transpose_to_first(0)
        res = evaluator.evaluate(m)
        if not res.passed:
            continue

        sr = SearchResult(
            melody=m,
            score=res.score,
            passed=res.passed,
            reason=res.reason,
            score_breakdown=tuple(res.score_breakdown),
            filter_trace=tuple(res.filter_trace),
            meta={
                "tried": tried,
                "n": n,
                "timestamp": time.time(),
            },
        )

        if best is None or sr.score > best[0]:
            best = (sr.score, sr)

    if best is None:
        # Zapisz też “porażkę”, żeby pipeline był deterministyczny.
        out = SearchResult(
            melody=random_walk(n=n, start=60).transpose_to_first(0),
            score=float("-inf"),
            passed=False,
            reason="No melody passed filters",
            meta={"tried": tried, "n": n, "timestamp": time.time()},
        )
        save_result_json("results/best.json", out)
        print("No melody passed. Wrote results/best.json anyway.")
        return

    _, sr = best
    save_result_json("results/best.json", sr)
    print("Wrote results/best.json")
    print("Best score:", sr.score)
    print("Melody:", sr.melody.pitches)


if __name__ == "__main__":
    # Upewnij się, że katalog results/ istnieje.
    main()
