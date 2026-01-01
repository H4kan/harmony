# audio/soundfont_renderer.py
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Optional

from core.melody import Melody
from audio.midi_writer import write_midi, MidiRenderConfig


@dataclass(frozen=True)
class SoundFontConfig:
    sf2_path: str
    sample_rate: int = 44100
    gain: float = 0.9


class SoundFontRenderer:
    def __init__(self, cfg: SoundFontConfig, fluidsynth_exe: Optional[str] = None):
        self.cfg = cfg
        # u Ciebie działa alias -> więc to jest OK:
        self.fluidsynth_exe = fluidsynth_exe or r"C:\tools\fluidsynth\bin\fluidsynth.exe"

        if not os.path.isfile(self.fluidsynth_exe):
            raise FileNotFoundError(f"fluidsynth.exe not found: {self.fluidsynth_exe}")
        if not os.path.isfile(self.cfg.sf2_path):
            raise FileNotFoundError(f"SF2 not found: {self.cfg.sf2_path}")

    def render_melody_to_wav(
        self,
        melody: Melody,
        wav_path: str,
        *,
        midi_tmp_path: str,
        midi_cfg: Optional[MidiRenderConfig] = None,
        keep_midi: bool = True,
    ) -> None:
        write_midi(melody, midi_tmp_path, cfg=midi_cfg)
        self.render_midi_to_wav(midi_tmp_path, wav_path)

        if not keep_midi:
            try:
                os.remove(midi_tmp_path)
            except OSError:
                pass

    def render_midi_to_wav(self, midi_path: str, wav_path: str) -> None:
        cmd = [
            self.fluidsynth_exe,
            "-ni",
            "-a", "file",
            "-o", f"audio.file.name={wav_path}",
            "-o", "audio.file.type=wav",
            "-o", f"synth.gain={self.cfg.gain}",
            "-r", str(self.cfg.sample_rate),
            self.cfg.sf2_path,
            midi_path,
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                "FluidSynth failed.\n"
                f"CMD: {' '.join(cmd)}\n"
                f"STDOUT:\n{proc.stdout}\n"
                f"STDERR:\n{proc.stderr}\n"
            )
