# scripts/render_elites_batch.py
from __future__ import annotations

import sys
import os
import json
from pathlib import Path

from core.io import load_result_json
from audio.midi_writer import MidiRenderConfig
from audio.soundfont_renderer import SoundFontRenderer, SoundFontConfig


def main() -> None:
    elites_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "results/elites")
    sf2_path = sys.argv[2] if len(sys.argv) > 2 else "soundfonts/piano.sf2"
    out_dir = Path(sys.argv[3] if len(sys.argv) > 3 else "results/elites_wav")

    out_dir.mkdir(parents=True, exist_ok=True)

    renderer = SoundFontRenderer(
        SoundFontConfig(sf2_path=str(sf2_path), gain=1.0)
    )

    midi_cfg = MidiRenderConfig(instrument_program=0, velocity=120)

    index_path = elites_dir / "index.json"
    with open(index_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    for it in items:
        json_file = elites_dir / it["file"]
        res = load_result_json(str(json_file))

        stem = json_file.stem
        wav_path = out_dir / f"{stem}.wav"
        mid_path = out_dir / f"{stem}.mid"

        renderer.render_melody_to_wav(
            res.melody,
            wav_path=str(wav_path),
            midi_tmp_path=str(mid_path),
            midi_cfg=midi_cfg,
            keep_midi=True,
        )

    print("Rendered", len(items), "files to", out_dir)


if __name__ == "__main__":
    main()
