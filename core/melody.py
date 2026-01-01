from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Melody:
    pitches: Tuple[int, ...]
    unit_duration: float = 0.25

    def __post_init__(self) -> None:
        if len(self.pitches) < 2:
            raise ValueError("Melody must have at least 2 pitches.")
        if self.unit_duration <= 0:
            raise ValueError("unit_duration must be > 0.")

    @property
    def n(self) -> int:
        return len(self.pitches)

    def intervals(self) -> Tuple[int, ...]:
        return tuple(
            self.pitches[i + 1] - self.pitches[i]
            for i in range(self.n - 1)
        )

    def abs_intervals(self) -> Tuple[int, ...]:
        return tuple(abs(d) for d in self.intervals())

    def pitch_classes(self, modulo: int = 12) -> Tuple[int, ...]:
        return tuple(p % modulo for p in self.pitches)

    def ambitus(self) -> int:
        return max(self.pitches) - min(self.pitches)

    def transpose_to_first(self, target: int = 0) -> "Melody":
        shift = target - self.pitches[0]
        return Melody(tuple(p + shift for p in self.pitches), self.unit_duration)
