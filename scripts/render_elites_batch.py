# scripts/render_elites_batch.py
from __future__ import annotations

import sys
import json
from pathlib import Path

from core.io import load_result_json
from core.runs import latest_run_dir
from audio.midi_writer import MidiRenderConfig
from audio.soundfont_renderer import SoundFontRenderer, SoundFontConfig


def main() -> None:
    # użycie:
    # python -m scripts.render_elites_batch [run_dir_or_base] [sf2] [limit]
    #
    # Przykłady:
    # python -m scripts.render_elites_batch results/elites soundfonts/piano.sf2 60
    # python -m scripts.render_elites_batch results/elites/run3 soundfonts/piano.sf2 80

    arg0 = sys.argv[1] if len(sys.argv) > 1 else "results/elites"
    sf2_path = sys.argv[2] if len(sys.argv) > 2 else "soundfonts/piano.sf2"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 80

    p = Path(arg0)

    # jeśli user podał base ("results/elites"), bierz najnowszy runN
    # jeśli podał już run ("results/elites/run7"), użyj go wprost
    if p.name.lower().startswith("run") and p.is_dir():
        run_dir = p
    else:
        run_dir = latest_run_dir(str(p))

    index_path = run_dir / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"index.json not found in: {run_dir}")

    mids_dir = run_dir / "mids"
    wavs_dir = run_dir / "wavs"
    mids_dir.mkdir(parents=True, exist_ok=True)
    wavs_dir.mkdir(parents=True, exist_ok=True)

    renderer = SoundFontRenderer(
        SoundFontConfig(sf2_path=str(sf2_path), gain=1.0)
    )

    midi_cfg = MidiRenderConfig(instrument_program=0, velocity=120)

    with open(index_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    # renderuj top-N po score
    items = sorted(items, key=lambda x: x["score"], reverse=True)[:limit]

    rendered = 0
    for it in items:
        json_file = run_dir / it["file"]
        res = load_result_json(str(json_file))

        stem = json_file.stem
        mid_path = mids_dir / f"{stem}.mid"
        wav_path = wavs_dir / f"{stem}.wav"

        renderer.render_melody_to_wav(
            res.melody,
            wav_path=str(wav_path),
            midi_tmp_path=str(mid_path),  # tu zapisujemy finalny MIDI
            midi_cfg=midi_cfg,
            keep_midi=True,
        )

        rendered += 1

    print("Run:", run_dir)
    print("Rendered:", rendered)
    print("MIDs ->", mids_dir)
    print("WAVs ->", wavs_dir)


if __name__ == "__main__":
    main()
