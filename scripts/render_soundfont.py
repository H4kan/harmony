# scripts/render_soundfont.py
from __future__ import annotations

import sys
from pathlib import Path

from core.io import load_result_json
from audio.midi_writer import MidiRenderConfig
from audio.soundfont_renderer import SoundFontRenderer, SoundFontConfig


def main() -> None:
    # python -m scripts.render_soundfont results/best.json soundfonts/piano.sf2 results/best.wav
    in_json = sys.argv[1] if len(sys.argv) > 1 else "results/best.json"
    sf2_path = sys.argv[2] if len(sys.argv) > 2 else "soundfonts/piano.sf2"
    out_wav = sys.argv[3] if len(sys.argv) > 3 else "results/best.wav"

    in_json_p = Path(in_json)
    out_wav_p = Path(out_wav)
    out_mid_p = out_wav_p.with_suffix(".mid")

    result = load_result_json(str(in_json_p))
    if not result.passed:
        print("WARNING: loaded result did not pass filters:", result.reason)

    renderer = SoundFontRenderer(
        SoundFontConfig(
            sf2_path=str(sf2_path),
            sample_rate=44100,
            gain=0.9,
        )
    )

    midi_cfg = MidiRenderConfig(
        instrument_program=0,  # piano (GM)
        velocity=110,
    )

    # render melody -> WAV + zostaw MIDI obok
    renderer.render_melody_to_wav(
        result.melody,
        wav_path=str(out_wav_p),
        midi_tmp_path=str(out_mid_p),
        midi_cfg=midi_cfg,
    )

    print("Read JSON:", in_json_p)
    print("Wrote MIDI:", out_mid_p)
    print("Wrote WAV :", out_wav_p)
    print("Score:", result.score)


if __name__ == "__main__":
    main()
