from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Tuple, Optional, List

from .melody import Melody


@dataclass(frozen=True)
class SearchResult:
    melody: Melody
    score: float
    passed: bool
    reason: str = ""
    score_breakdown: Tuple[Tuple[str, float], ...] = ()
    filter_trace: Tuple[Tuple[str, bool, str], ...] = ()
    meta: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "melody": {
                "pitches": list(self.melody.pitches),
                "unit_duration": self.melody.unit_duration,
            },
            "score": self.score,
            "passed": self.passed,
            "reason": self.reason,
            "score_breakdown": [[n, v] for (n, v) in self.score_breakdown],
            "filter_trace": [[n, ok, r] for (n, ok, r) in self.filter_trace],
            "meta": self.meta or {},
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "SearchResult":
        m = d["melody"]
        melody = Melody(tuple(m["pitches"]), float(m.get("unit_duration", 0.25)))
        return SearchResult(
            melody=melody,
            score=float(d["score"]),
            passed=bool(d["passed"]),
            reason=str(d.get("reason", "")),
            score_breakdown=tuple((str(n), float(v)) for n, v in d.get("score_breakdown", [])),
            filter_trace=tuple((str(n), bool(ok), str(r)) for n, ok, r in d.get("filter_trace", [])),
            meta=dict(d.get("meta", {})),
        )


def save_result_json(path: str, result: SearchResult) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)


def load_result_json(path: str) -> SearchResult:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return SearchResult.from_dict(data)
