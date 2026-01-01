# scripts/search_map_elites.py
from __future__ import annotations

import time
import random
import platform
import sys
import re

RANDOM_SEED = 1337

from evaluation.filters import (
    MaxStepFilter,
    AmbitusFilter,
    # TurnsRateFilter,
    # PitchClassConcentrationFilter,
)
from evaluation.scorers import (
    BellCurveIntervalScorer,
    MotifNGramScorer,
    ClimaxPlacementScorer,
    EndNearStartScorer,
    IntervalEntropyScorer,
    TurnsTargetScorer,
    PitchClassTop3TargetScorer
)
from evaluation.evaluator import MelodyEvaluator

from search.map_elites import MapElites, MapElitesConfig, MutationConfig, DescriptorConfig

from core.runs import next_run_dir

from dataclasses import asdict, is_dataclass

def to_dict(x):
    if is_dataclass(x):
        return asdict(x)
    if isinstance(x, (list, tuple)):
        return [to_dict(v) for v in x]
    if isinstance(x, dict):
        return {k: to_dict(v) for k, v in x.items()}
    # fallback: spróbuj wyciągnąć prosty __dict__
    if hasattr(x, "__dict__"):
        return {k: to_dict(v) for k, v in x.__dict__.items() if not k.startswith("_")}
    return x

def main() -> None:
    evaluator = MelodyEvaluator(
        filters=[
            MaxStepFilter(max_abs_step=7),
            AmbitusFilter(max_ambitus=14),
            # TurnsRateFilter(max_rate=0.40),
            # PitchClassConcentrationFilter(min_top3_ratio=0.40),
        ],
        scorers=[
            BellCurveIntervalScorer(target=2.5, width=1.2, weight=1.0),
            MotifNGramScorer(ngram=4, min_repeats=2, weight=0.8),
            ClimaxPlacementScorer(low=0.45, high=0.85, weight=1.0),
            EndNearStartScorer(tolerance=2, weight=0.8),
            IntervalEntropyScorer(target_bits=2.2, width=1.0, weight=1.2),
            TurnsTargetScorer(target=0.25, width=0.12, weight=1.0),
            PitchClassTop3TargetScorer(target=0.65, width=0.18, weight=0.8),
        ],
    )

    cfg = MapElitesConfig(
        n_notes=32,
        start_pitch=0,
        init_random=5000,
        iterations=80000,
        mutation=MutationConfig(
            step_set=(-5,-4,-3,-2,-1,0,1,2,3,4,5,7,-7,9,-9),
            point_mut_min=1,
            point_mut_max=3,
            motif_prob=0.35,
            motif_len_min=3,
            motif_len_max=6,
        ),
        descriptor=DescriptorConfig(
            max_ambitus_bin=24,
            turn_rate_step=0.05,
        ),
        max_elites_to_save=20,
    )

    timestamp_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    evaluator_meta = {
        "filters": [{"type": f.__class__.__name__, "params": to_dict(f)} for f in evaluator.filters],
        "scorers": [{"type": s.__class__.__name__, "params": to_dict(s)} for s in evaluator.scorers],
    }

    run_dir = next_run_dir("results/elites")
    
    run_name = run_dir.name  # np. "run7"
    m = re.match(r"run(\d+)$", run_name, re.IGNORECASE)
    run_id = int(m.group(1)) if m else 1

    random.seed(RANDOM_SEED)

    run_meta = {
        "created_utc": timestamp_utc,
        "run_dir": str(run_dir),
        "run_id": run_id,
        "seed": RANDOM_SEED,
        "python": {"version": sys.version, "platform": platform.platform()},
        "map_elites_config": to_dict(cfg),
        "evaluator": evaluator_meta,
    }

    me = MapElites(evaluator, cfg)
    archive = me.run()
    print("Archive size (filled niches):", len(archive))

    me.save_archive(str(run_dir), run_meta=run_meta)
    print("Saved elites to:", run_dir)
    print("Index:", run_dir / "index.json")



if __name__ == "__main__":
    main()
