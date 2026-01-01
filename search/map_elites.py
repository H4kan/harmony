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
    reverse_prob: float = 0.15
    tilt_prob: float = 0.20
    tilt_len_min: int = 4
    tilt_len_max: int = 10


def clamp_to_step_set(v: int, step_set: Tuple[int, ...]) -> int:
    # wybiera najbliższy do v element z step_set
    return min(step_set, key=lambda s: abs(s - v))

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

    # 3) reverse fragment (zmiana dramaturgii bez rozwalania statów)
    if random.random() < cfg.reverse_prob and len(out) >= 6:
        L = random.randint(3, min(10, len(out)))
        i = random.randrange(0, len(out) - L + 1)
        frag = out[i:i + L]
        out[i:i + L] = list(reversed(frag))

    # 4) tilt fragmentu: dodaj +1/-1 do sekwencji (z clampem do step_set)
    if random.random() < cfg.tilt_prob and len(out) >= cfg.tilt_len_min:
        L = random.randint(cfg.tilt_len_min, min(cfg.tilt_len_max, len(out)))
        i = random.randrange(0, len(out) - L + 1)
        sign = random.choice((-1, 1))
        for j in range(i, i + L):
            out[j] = clamp_to_step_set(out[j] + sign, cfg.step_set)

    return out

def interval_ngrams(intervals: List[int], n: int = 4) -> set[tuple[int, ...]]:
    if len(intervals) < n:
        return set()
    return {tuple(intervals[i:i+n]) for i in range(len(intervals) - n + 1)}

def novelty_against(elite: Elite, others: List[Elite], ngram_n: int = 4) -> float:
    ints = pitches_to_intervals(elite.melody.pitches)
    A = interval_ngrams(ints, n=ngram_n)
    if not others or not A:
        return 1.0
    best = 0.0
    for o in others:
        B = interval_ngrams(pitches_to_intervals(o.melody.pitches), n=ngram_n)
        if not B:
            continue
        inter = len(A & B)
        union = len(A | B)
        sim = inter / union if union else 0.0  # Jaccard similarity
        best = max(best, sim)
    return 1.0 - best  # 1 = bardzo inne, 0 = bardzo podobne

# ---------- opis niszy (descriptor) ----------

@dataclass(frozen=True)
class DescriptorConfig:
    # ambitus: koszykujemy co 1 półton, ale obcinamy do max_ambitus_bin
    max_ambitus_bin: int = 24

    # turn_rate: koszykujemy w krokach (np. 0.05 => 21 koszy 0..1)
    turn_rate_step: float = 0.05
    max_turn_rate: float = 1.0


def descriptor_from_stats(stats: MelodyStats, cfg: DescriptorConfig) -> Tuple[int, int, int]:
    a = min(stats.ambitus, cfg.max_ambitus_bin)

    denom = max(1, stats.n - 2)
    turn_rate = stats.turns / denom
    turn_rate = max(0.0, min(cfg.max_turn_rate, float(turn_rate)))
    tbin = int(turn_rate / cfg.turn_rate_step + 1e-9)

    used_pc = sum(1 for c in stats.pitch_class_hist if c > 0)  # 1..12
    pcbin = used_pc  # bez koszykowania, już jest 1..12

    return (a, tbin, pcbin)


# ---------- MAP-Elites ----------

@dataclass
class MapElitesConfig:
    n_notes: int = 32
    start_pitch: int = 0  # relatywnie; MIDI mapping robisz później w rendererze
    init_random: int = 20000  # ile losowych prób na start, żeby zasilić archiwum
    iterations: int = 300000  # ile mutacji / prób zasiedlenia nisz

    mutation: MutationConfig = MutationConfig()
    descriptor: DescriptorConfig = DescriptorConfig()

    # jeśli True: zapisuj tylko te, co przechodzą filtry
    require_passed: bool = True

    # ile elit max zapisujemy (limit plików)
    max_elites_to_save: int = 300


EliteKey = Tuple[int, int, int]


@dataclass
class Elite:
    melody: Melody
    score: float
    key: EliteKey


class MapElites:
    def __init__(self, evaluator, cfg: MapElitesConfig):
        self.evaluator = evaluator
        self.cfg = cfg
        self.archive: Dict[EliteKey, List[Elite]] = {}
        self.per_cell: int = 3  # top-3 na niszę

    def _random_candidate(self) -> Melody:
        mode = random.random()
        n_int = self.cfg.n_notes - 1

        # Mode A: stepwise (prawie same małe kroki)
        if mode < 0.45:
            small = (-2, -1, 0, 1, 2)
            big = tuple(d for d in self.cfg.mutation.step_set if abs(d) >= 3)
            intervals = []
            for _ in range(n_int):
                if random.random() < 0.90:
                    intervals.append(random.choice(small))
                else:
                    intervals.append(random.choice(big) if big else random.choice(small))

        # Mode B: arpeggio-ish (częściej tercje/kwarty/kwinty)
        elif mode < 0.75:
            arp = (0, 3, -3, 4, -4, 5, -5)
            spice = tuple(self.cfg.mutation.step_set)
            intervals = []
            for _ in range(n_int):
                if random.random() < 0.85:
                    intervals.append(random.choice(arp))
                else:
                    intervals.append(random.choice(spice))

        # Mode C: phrase arches (4 frazy po 8, łuki)
        else:
            intervals = []
            phrase_len = 8
            for _phrase in range(max(1, self.cfg.n_notes // phrase_len)):
                # pół frazy w górę, pół w dół (z szumem)
                up_len = phrase_len // 2
                down_len = phrase_len - up_len
                for _ in range(up_len):
                    intervals.append(random.choice((1, 1, 2, 0, 2, 1)))
                for _ in range(down_len):
                    intervals.append(random.choice((-1, -1, -2, 0, -2, -1)))
            intervals = intervals[:n_int]

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
        cell = self.archive.get(elite.key)
        if cell is None:
            self.archive[elite.key] = [elite]
            return True

        # jeśli już mamy prawie identyczną, nie dodawaj (novelty cutoff)
        nov = novelty_against(elite, cell, ngram_n=4)
        if nov < 0.15:
            return False

        cell.append(elite)

        # sort: najpierw score, ale jak score zbliżone, wolisz bardziej novel
        cell.sort(key=lambda e: (e.score, novelty_against(e, cell, ngram_n=4)), reverse=True)

        # obetnij do top-N
        changed = len(cell) > self.per_cell
        self.archive[elite.key] = cell[: self.per_cell]
        return True or changed

    def _pick_parent(self) -> Optional[Elite]:
        if not self.archive:
            return None
        cell = random.choice(list(self.archive.values()))
        return random.choice(cell)

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

    def save_archive(self, out_dir: str, run_meta: Optional[dict] = None) -> None:
        os.makedirs(out_dir, exist_ok=True)

        # spłaszcz archiwum: (key, elite, k)
        flat: List[tuple[EliteKey, Elite, int]] = []
        for key, cell in self.archive.items():
            for k, elite in enumerate(cell):
                flat.append((key, elite, k))

        # sortuj globalnie po score
        flat.sort(key=lambda x: x[1].score, reverse=True)

        # ogranicz liczbę zapisywanych elit
        flat = flat[: self.cfg.max_elites_to_save]

        index = []

        for key, elite, k in flat:
            a, t, pc = key
            fname = f"elite_a{a:02d}_t{t:02d}_pc{pc:02d}_k{k:02d}.json"
            path = os.path.join(out_dir, fname)

            sr = SearchResult(
                melody=elite.melody,
                score=elite.score,
                passed=True,
                reason="",
                score_breakdown=(),
                filter_trace=(),
                meta={
                    "descriptor": {
                        "ambitus_bin": a,
                        "turn_rate_bin": t,
                        "pc_bin": pc,
                        "cell_rank": k,
                    },
                    "n_notes": self.cfg.n_notes,
                    "run": run_meta or {},
                },
            )

            save_result_json(path, sr)

            index.append({
                "file": fname,
                "score": elite.score,
                "ambitus_bin": a,
                "turn_rate_bin": t,
                "pc_bin": pc,
                "cell_rank": k,
                "n_notes": self.cfg.n_notes,
            })

        with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
