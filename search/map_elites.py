# search/map_elites.py
from __future__ import annotations

import os
import json
import random
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List, Iterable

from core.melody import Melody
from core.stats import MelodyStats
from core.io import SearchResult, save_result_json


# ---------- pomocnicze: pitches <-> intervals ----------

def pitches_to_intervals(pitches: Tuple[int, ...]) -> List[int]:
    return [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]


def intervals_to_pitches(start: int, intervals: List[int]) -> Tuple[int, ...]:
    x = [start]
    for d in intervals:
        x.append(x[-1] + int(d))
    return tuple(x)


# ---------- mutacje ----------

@dataclass(frozen=True)
class MutationConfig:
    step_set: Tuple[int, ...] = (-4, -3, -2, -1, 0, 1, 2, 3, 4, 7, -7)
    # ile “miejsc” zmieniamy w interwałach
    point_mut_min: int = 1
    point_mut_max: int = 3
    # szansa na mutację motywową
    motif_prob: float = 0.35
    motif_len_min: int = 3
    motif_len_max: int = 6


def mutate_intervals(intervals: List[int], cfg: MutationConfig) -> List[int]:
    out = intervals[:]

    # 1) point mutations
    k = random.randint(cfg.point_mut_min, cfg.point_mut_max)
    for _ in range(k):
        i = random.randrange(len(out))
        out[i] = random.choice(cfg.step_set)

    # 2) motif copy/paste (czasem)
    if random.random() < cfg.motif_prob and len(out) >= cfg.motif_len_min * 2:
        L = random.randint(cfg.motif_len_min, min(cfg.motif_len_max, len(out) // 2))
        src = random.randrange(0, len(out) - L + 1)
        dst = random.randrange(0, len(out) - L + 1)
        if src != dst:
            motif = out[src:src + L]
            out[dst:dst + L] = motif

    return out


# ---------- opis niszy (descriptor) ----------

@dataclass(frozen=True)
class DescriptorConfig:
    # ambitus: koszykujemy co 1 półton, ale obcinamy do max_ambitus_bin
    max_ambitus_bin: int = 24

    # turn_rate: koszykujemy w krokach (np. 0.05 => 21 koszy 0..1)
    turn_rate_step: float = 0.05
    max_turn_rate: float = 1.0


def descriptor_from_stats(stats: MelodyStats, cfg: DescriptorConfig) -> Tuple[int, int]:
    # ambitus bin
    a = min(stats.ambitus, cfg.max_ambitus_bin)

    # turn_rate bin
    denom = max(1, stats.n - 2)
    turn_rate = stats.turns / denom
    turn_rate = max(0.0, min(cfg.max_turn_rate, float(turn_rate)))
    tbin = int(turn_rate / cfg.turn_rate_step + 1e-9)

    return (a, tbin)


# ---------- MAP-Elites ----------

@dataclass
class MapElitesConfig:
    n_notes: int = 32
    start_pitch: int = 0  # relatywnie; MIDI mapping robisz później w rendererze
    init_random: int = 3000  # ile losowych prób na start, żeby zasilić archiwum
    iterations: int = 50000  # ile mutacji / prób zasiedlenia nisz

    mutation: MutationConfig = MutationConfig()
    descriptor: DescriptorConfig = DescriptorConfig()

    # jeśli True: zapisuj tylko te, co przechodzą filtry
    require_passed: bool = True

    # ile elit max zapisujemy (limit plików)
    max_elites_to_save: int = 300


EliteKey = Tuple[int, int]


@dataclass
class Elite:
    melody: Melody
    score: float
    key: EliteKey


class MapElites:
    def __init__(self, evaluator, cfg: MapElitesConfig):
        self.evaluator = evaluator
        self.cfg = cfg
        self.archive: Dict[EliteKey, Elite] = {}

    def _random_candidate(self) -> Melody:
        # losowe interwały z step_set
        intervals = [random.choice(self.cfg.mutation.step_set) for _ in range(self.cfg.n_notes - 1)]
        pitches = intervals_to_pitches(self.cfg.start_pitch, intervals)
        return Melody(pitches)

    def _evaluate(self, melody: Melody) -> Optional[Elite]:
        res = self.evaluator.evaluate(melody)
        if self.cfg.require_passed and not res.passed:
            return None

        # stats do descriptor
        stats = res.stats if getattr(res, "stats", None) is not None else MelodyStats.compute(melody)
        key = descriptor_from_stats(stats, self.cfg.descriptor)
        return Elite(melody=melody, score=float(res.score), key=key)

    def _try_insert(self, elite: Elite) -> bool:
        cur = self.archive.get(elite.key)
        if cur is None or elite.score > cur.score:
            self.archive[elite.key] = elite
            return True
        return False

    def _pick_parent(self) -> Optional[Elite]:
        if not self.archive:
            return None
        return random.choice(list(self.archive.values()))

    def run(self) -> Dict[EliteKey, Elite]:
        # 1) inicjalizacja archiwum losowo
        for _ in range(self.cfg.init_random):
            m = self._random_candidate()
            e = self._evaluate(m)
            if e is not None:
                self._try_insert(e)

        # 2) pętla MAP-Elites
        for _ in range(self.cfg.iterations):
            parent = self._pick_parent()
            if parent is None:
                # jeśli archiwum puste (np. filtry zbyt ostre), próbuj dalej losowo
                m = self._random_candidate()
                e = self._evaluate(m)
                if e is not None:
                    self._try_insert(e)
                continue

            ints = pitches_to_intervals(parent.melody.pitches)
            ints2 = mutate_intervals(ints, self.cfg.mutation)
            pitches2 = intervals_to_pitches(self.cfg.start_pitch, ints2)
            child = Melody(pitches2)

            e2 = self._evaluate(child)
            if e2 is not None:
                self._try_insert(e2)

        return self.archive

    def save_archive(self, out_dir: str) -> None:
        os.makedirs(out_dir, exist_ok=True)

        # sort elit po score malejąco, ogranicz ilość zapisu
        elites_sorted = sorted(self.archive.values(), key=lambda e: e.score, reverse=True)
        elites_sorted = elites_sorted[: self.cfg.max_elites_to_save]

        index = []
        for e in elites_sorted:
            a, t = e.key
            fname = f"elite_a{a:02d}_t{t:02d}.json"
            path = os.path.join(out_dir, fname)

            sr = SearchResult(
                melody=e.melody,
                score=e.score,
                passed=True,
                reason="",
                score_breakdown=(),
                filter_trace=(),
                meta={
                    "descriptor": {"ambitus_bin": a, "turn_rate_bin": t},
                    "n_notes": self.cfg.n_notes,
                },
            )
            save_result_json(path, sr)

            index.append({
                "file": fname,
                "score": e.score,
                "ambitus_bin": a,
                "turn_rate_bin": t,
                "n_notes": self.cfg.n_notes,
            })

        with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
