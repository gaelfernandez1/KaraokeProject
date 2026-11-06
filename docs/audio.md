# Audio

How the engine separates the vocals, how it leaves the package's audio and how the web app plays
it. The numbers and the reason behind each choice are in
[`plan-v3/decisiones/004-audio.md`](plan-v3/decisiones/004-audio.md) (in Spanish).

## Separating the vocals

`karaoke_engine.separation.RoformerSeparator` wraps
[audio-separator](https://github.com/nomadkaraoke/python-audio-separator) and implements the
engine's `Separator` step. It needs the `ml` extra (`uv sync --extra ml`).

```toml
[steps.separator]
target = "karaoke_engine.separation:RoformerSeparator"
params = { model = "vocals_mel_band_roformer.ckpt", segment_size = 801 }
```

| Parameter | Default | What it does |
|---|---|---|
| `model` | — | the model file in audio-separator's catalogue |
| `vocals_stem` | `"Vocals"` | the stem that is the voice (case-insensitive) |
| `segment_size` | the model's | STFT frames per chunk: fewer means less VRAM |
| `overlap` | 2 | overlapping passes per chunk (8 takes four times as long) |
| `autocast` | `true` | fp16 on the GPU |
| `model_dir` | `~/.cache/karaoke/models/audio-separator` | where the models are downloaded |

The first run downloads the model, 0.6 to 1.7 GB. The pipelines `bench/pipelines/sep-*.toml` are
the candidates that were measured. To measure another one, copy one, change the model and follow
[`benchmark.md`](benchmark.md).

If you change a parameter's default, bump `version` in the class: the benchmark does not keep
defaults in its cache key.

## The package's audio

`karaoke_engine.audio` does three things:

- decodes anything ffmpeg reads, video included;
- measures loudness (EBU R128);
- writes the package's stems to `instrumental.m4a` and `vocals.m4a`: AAC-LC at 44.1 kHz,
  `+faststart`, the mix at −14 LUFS, and neither the mix nor the stems above −1 dBTP.

To bring a package whose stems are in another format (WAV, for example) to the package format, work
on a copy outside the repository, because the command rewrites `karaoke.json`:

```bash
cp -r fixtures/packages/cortez-feel-stripped bench/data/paquetes/cortez-feel-stripped-m4a
uv run karaoke audio bench/data/paquetes/cortez-feel-stripped-m4a --mix bench/data/jamendo/Cortez_-_Feel__Stripped_/audio.mp3
```

Without `--mix`, the mix is rebuilt by adding the stems. The command updates `audio` in
`karaoke.json` and validates the package; the old files stay and can be deleted.

## Playing in the browser

`web/src/lib/audio/` holds the player's engine, with no interface:

```ts
import { AudioEngine } from '#lib/audio/engine.js';

const engine = new AudioEngine(new AudioContext());
await engine.load({ instrumental: 'package/instrumental.m4a', vocals: 'package/vocals.m4a' });
await engine.play(); // also pause(), seek(s)
engine.setVocalVolume(0.3); // guide vocals, 0 to 1
await engine.setPitch(-2); // semitones, −12 to 12
engine.setManualOffset(0.12); // the device's calibration, in seconds
const t = engine.now(); // what is heard now: the lyrics follow this
```

- `clock.ts`: the clock (`SongClock`), which tells what plays in the audio graph apart from what
  reaches the ear.
- `calibration.ts`: estimates the delay from the user's clicks and taps.

The tests (`pnpm --dir web test`) use a fake `AudioContext`.

What only shows on a real device is tried in the app itself: the player (`/cantar/<id>`, the
«Son» panel) for the guide vocals and the pitch, and `/axustes` to calibrate the delay over HDMI
or Bluetooth. With `pnpm --dir web dev`, the development server serves the packages in
`fixtures/packages/` and `bench/data/paquetes/` under `/media/` (see [`web.md`](web.md)). To open
it from a phone on the same network:

```bash
pnpm --dir web dev --host
```

Two things to keep in mind when trying it from a phone:

- **WSL**: in the default network mode (NAT), the phone cannot reach the server. There are two
  ways out:
  - set `networkingMode=mirrored` under `[wsl2]` in `%UserProfile%\.wslconfig` and run
    `wsl --shutdown`;
  - or a `netsh interface portproxy` on Windows, which needs administrator rights.
- **Pitch shifting** uses an `AudioWorklet`, which browsers only allow over HTTPS or on
  `localhost`. Through `http://<ip>:5173` everything else works, but not the pitch. On Android it
  can be tried: connect the phone by USB and forward port 5173 from `chrome://inspect` (Port
  forwarding). The phone then opens `http://localhost:5173/axustes` or a song.
