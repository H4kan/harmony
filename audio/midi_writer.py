# audio/midi_writer.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pretty_midi

from core.melody import Melody


@dataclass(frozen=True)
class MidiRenderConfig:
    instrument_program: int = 0  # GM: 0 = Acoustic Grand Piano
    velocity: int = 100
    # Docelowy rejestr MIDI (środek melodii)
    target_center_midi: int = 60  # C4
    # Bezpieczne granice MIDI
    min_midi: int = 36  # C2
    max_midi: int = 96  # C7


def _clamp(v: int, lo: int, hi: int) -> int:
    return lo if v < lo else hi if v > hi else v


def _shift_to_midi_range(pitches: Tuple[int, ...], cfg: MidiRenderConfig) -> Tuple[int, ...]:
    """
    Przesuwa całą melodię (transpozycja) tak, żeby:
    - była w zakresie [min_midi, max_midi]
    - i była możliwie blisko target_center_midi (mniej więcej w środku klawiatury)
    """
    mn = min(pitches)
    mx = max(pitches)

    # Jeśli to już wygląda jak MIDI (np. 40..80), zostaw, ale dalej dopilnuj zakresu.
    # Jeśli to skala relatywna (np. -7..12), przeniesiemy ją w okolice target_center.
    center = (mn + mx) / 2.0
    shift = int(round(cfg.target_center_midi - center))

    shifted = [p + shift for p in pitches]

    # Jeśli po przesunięciu nadal wychodzimy poza zakres, dociągnij dodatkowo.
    mn2, mx2 = min(shifted), max(shifted)
    if mn2 < cfg.min_midi:
        delta = cfg.min_midi - mn2
        shifted = [p + delta for p in shifted]
    if mx2 > cfg.max_midi:
        delta = cfg.max_midi - mx2
        shifted = [p + delta for p in shifted]

    # Finalnie i tak clamp (na wszelki wypadek)
    shifted = [_clamp(p, 0, 127) for p in shifted]
    return tuple(shifted)


def write_midi(melody: Melody, path: str, cfg: Optional[MidiRenderConfig] = None) -> None:
    cfg = cfg or MidiRenderConfig()

    # 1) Mapowanie do bezpiecznego MIDI
    midi_pitches = _shift_to_midi_range(melody.pitches, cfg)

    # 2) Walidacja velocity
    velocity = _clamp(int(cfg.velocity), 0, 127)

    pm = pretty_midi.PrettyMIDI()
    instr = pretty_midi.Instrument(program=int(cfg.instrument_program))

    t = 0.0
    dur = float(melody.unit_duration)

    for p in midi_pitches:
        # p już jest 0..127
        note = pretty_midi.Note(
            velocity=velocity,
            pitch=int(p),
            start=t,
            end=t + dur,
        )
        instr.notes.append(note)
        t += dur

    pm.instruments.append(instr)
    pm.write(path)
