# Audio

Cómo separa la voz el motor, cómo deja el audio del paquete y cómo lo reproduce la web. Las cifras
y el porqué de cada elección están en `docs/plan-v3/decisiones/004-audio.md`.

## Separar la voz

`karaoke_engine.separation.RoformerSeparator` envuelve
[audio-separator](https://github.com/nomadkaraoke/python-audio-separator) y cumple el paso
`Separator` del motor. Necesita el extra `ml` (`uv sync --extra ml`).

```toml
[steps.separator]
target = "karaoke_engine.separation:RoformerSeparator"
params = { model = "vocals_mel_band_roformer.ckpt", segment_size = 801 }
```

| Parámetro | Por defecto | Qué hace |
|---|---|---|
| `model` | — | fichero del modelo en el catálogo de audio-separator |
| `vocals_stem` | `"Vocals"` | stem que hace de voz (sin distinguir mayúsculas) |
| `segment_size` | el del modelo | marcos STFT por trozo: menos, menos VRAM |
| `overlap` | 2 | pasadas solapadas por trozo (8 tarda cuatro veces más) |
| `autocast` | `true` | fp16 en la GPU |
| `model_dir` | `~/.cache/karaoke/models/audio-separator` | dónde se descargan los modelos |

La primera vez descarga el modelo, de 0,6 a 1,7 GB. Los pipelines `bench/pipelines/sep-*.toml` son
los candidatos medidos. Para medir otro, copia uno, cambia el modelo y sigue `docs/banco.md`.

Si cambias el valor por defecto de un parámetro, sube `version` en la clase: el banco no guarda los
valores por defecto en la clave de la caché.

## Audio del paquete

`karaoke_engine.audio` hace estas tres cosas:

- decodifica cualquier cosa que lea ffmpeg, vídeo incluido;
- mide la sonoridad (EBU R128);
- escribe los stems del paquete en `instrumental.m4a` y `vocals.m4a`: AAC-LC a 44,1 kHz,
  `+faststart`, la mezcla a −14 LUFS y como mucho −1 dBTP.

Para pasar al formato del paquete uno que ya tiene stems en otro formato (WAV, por ejemplo):

```bash
uv run karaoke audio fixtures/packages/cortez-feel-stripped --mix bench/data/jamendo/Cortez_-_Feel__Stripped_/audio.mp3
```

Sin `--mix`, la mezcla se reconstruye sumando los stems. El comando actualiza `audio` en
`karaoke.json` y valida el paquete.

## Reproducir en la web

`web/src/lib/audio/` tiene el motor del reproductor, sin interfaz:

```ts
import { AudioEngine } from '#lib/audio/engine.js';

const engine = new AudioEngine(new AudioContext());
await engine.load({ instrumental: 'paquete/instrumental.m4a', vocals: 'paquete/vocals.m4a' });
await engine.play(); // también pause(), seek(s)
engine.setVocalVolume(0.3); // voz guía, de 0 a 1
await engine.setPitch(-2); // semitonos, de −12 a 12
engine.setManualOffset(0.12); // calibración del dispositivo, en segundos
const t = engine.now(); // lo que se oye ahora: la letra sigue esto
```

- `clock.ts`: el reloj (`SongClock`), que separa lo que suena en el grafo de audio de lo que llega
  al oído.
- `calibration.ts`: estima el retardo a partir de clics y toques del usuario.

Los tests (`pnpm --dir web test`) usan un `AudioContext` falso.

Lo que solo se ve en un aparato real se prueba en `/proba-audio`: retardo por HDMI o Bluetooth, el
cambio de tono en el móvil, la memoria. Esa página solo funciona con `pnpm --dir web dev`, que
sirve en `/paquetes/` los paquetes de `fixtures/packages/` y `bench/data/paquetes/`. Para abrirla
desde el móvil, en la misma red:

```bash
pnpm --dir web dev --host
```

Ten en cuenta dos cosas al probar desde el móvil:

- **WSL**: en el modo de red por defecto (NAT), el móvil no llega al servidor. Hay dos salidas:
  - poner `networkingMode=mirrored` en `[wsl2]` de `%UserProfile%\.wslconfig` y hacer
    `wsl --shutdown`;
  - o un `netsh interface portproxy` en Windows, que pide administrador.
- **Cambio de tono**: usa un `AudioWorklet`, y los navegadores solo lo dan en HTTPS o en
  `localhost`. Por `http://<ip>:5173` el resto funciona, pero el tono no. En Android sí se puede
  probar: conecta el móvil por USB y reenvía el puerto 5173 desde `chrome://inspect` (Port
  forwarding). El móvil abre entonces `http://localhost:5173/proba-audio`.
