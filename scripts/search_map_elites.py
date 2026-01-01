# scripts/search_map_elites.py
from __future__ import annotations

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

from search.map_elites import MapElites, MapElitesConfig, MutationConfig, DescriptorConfig


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

    cfg = MapElitesConfig(
        n_notes=32,
        start_pitch=0,
        init_random=5000,
        iterations=80000,
        mutation=MutationConfig(
            step_set=(-4, -3, -2, -1, 0, 1, 2, 3, 4, 7, -7),
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
        max_elites_to_save=300,
    )

    me = MapElites(evaluator, cfg)
    archive = me.run()
    print("Archive size (filled niches):", len(archive))

    out_dir = "results/elites"
    me.save_archive(out_dir)
    print("Saved elites to:", out_dir)
    print("Index:", out_dir + "/index.json")


if __name__ == "__main__":
    main()
