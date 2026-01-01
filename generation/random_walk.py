import random
from core.melody import Melody


def random_walk(
    n: int,
    start: int = 60,
    steps=(-4, -3, -2, -1, 0, 1, 2, 3, 4),
) -> Melody:
    pitches = [start]
    for _ in range(n - 1):
        pitches.append(pitches[-1] + random.choice(steps))
    return Melody(tuple(pitches))
