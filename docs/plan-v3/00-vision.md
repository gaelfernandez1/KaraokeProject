# Plan v3 · Visión, arquitectura y contratos

> Fuente de verdad del plan v3 del KaraokeProject (escrito el 28/10/2026). Sustituye a todo lo
> anterior: plan v2, `docs/00–10`, `docs/planning/STATE.md` y las secciones del CLAUDE.md antiguo
> que hablan de fases V1–V8. Si algo de aquí cambia, se cambia con una decisión escrita
> (`decisiones/`, ver §10) y se actualiza este documento en el mismo PR.

## 0. Cómo se usa

- Cada área de mejora se trabaja en una conversación de Claude Code distinta (C1–C10, §8). Sus
  prompts están en `01-conversaciones.md`.
- Todas leen este documento, `ESTADO.md` y `decisiones/` al empezar. Así el resultado de todas
  encaja.
- Lo marcado como **decisión inicial** lo eligió la conversación de planificación. La conversación
  dueña puede cambiarlo si lo justifica en una decisión escrita.

## 1. Objetivo

Con palabras del usuario (28/10/2026, resumidas): una mejora masiva de todo el proyecto (backend,
frontend, herramientas, código y forma de trabajar), con libertad total para cambiar cómo se hace
mientras se mantenga el objetivo: **un karaoke que funcione en muchos idiomas pero sobre todo en
gallego, bien transcrito, con subtítulos animados que vayan al mismo tiempo que se canta**. Debe
funcionar **con cualquier canción** y **en cualquier contexto: en el móvil, en el portátil y en la
tele conectando el HDMI**, con **un sonido que funcione bien en todo y tenga algo chulo**. Da igual
cómo se haga: si algo (por ejemplo, las sílabas) no tiene sentido, se hace de otra forma mejor.

Qué significa éxito (metas **provisionales**; C2 las fija tras medir la línea base):

| Qué | Meta provisional |
|---|---|
| Sincronía con letra dada | mediana del error de inicio de palabra ≤ 0,10 s y ≥ 90 % de palabras a ≤ 0,30 s, en es/en (JamendoLyrics) y en el conjunto gallego propio |
| Transcripción sin letra (gl) | WER claramente menor que la línea base; cifra fijada tras medir |
| Idioma | 0 casos de cambio silencioso de idioma en todo el banco |
| Velocidad | canción de 4 min lista en ≤ 4 min en la RTX 3050 (sin contar la primera descarga de modelos); MP4 1080p de 4 min en ≤ 1 min |
| Reproductor | animación fluida (60 fps) en un móvil medio; legible a 3 m en una tele 1080p; desfase entre audio y letra ajustable |
| Corrección | arreglar una palabra o un tiempo en segundos, sin reprocesar la canción |

## 2. Punto de partida (diagnóstico del 28/10/2026)

- **Pipeline viejo**: Demucs 4.0.1 → faster-whisper 1.0.1 `small` en CPU forzada + WhisperX 3.1.3
  → MoviePy + PIL redibujando cada fotograma y codificando el vídeo dos veces.
- **Gallego**: la web nunca pasa el idioma (no hay selector); se adivina con Whisper `small`, que
  confunde gallego con español o portugués; el VAD de WhisperX 3.1.3 está roto (URL muerta) y, si
  falla, el código cae a **inglés** (`src/whisperx_service/api.py`). Las sílabas salen de `pyphen`
  (guionado tipográfico) y el resaltado ilumina un porcentaje aproximado de sílabas de la línea, no
  usa tiempos reales (`karaoke_rendering.py`). Leído en el código, no ejecutado.
- **Web**: Flask 2.3 + Jinja + Bootstrap, Celery + Redis, Postgres, R2, magic links (Resend),
  Sentry. Nada desplegado. Rama `feature/f13-deploy` con 5 commits sin mergear.
- **Entorno**: Python 3.10 (fin de soporte en octubre de 2026). En WSL no hay docker, uv, gh ni
  ffmpeg; la GPU sí se ve (`nvidia-smi`).
- `docs/` y `CLAUDE.md` están en `.gitignore` (C1 lo cambia para que el plan se versione).

## 3. Principios

1. **Gallego primero.** El usuario elige el idioma (gallego por defecto); la detección solo sugiere.
   Nunca se cambia de idioma en silencio. Si falta un recurso gallego para un paso, se usa el mejor
   disponible y queda anotado en `provenance`.
2. **Medir antes de elegir.** Modelos y parámetros se eligen con el banco de pruebas (C2), no por
   opinión. Cada cambio que afecte a calidad o velocidad se mide.
3. **Un único documento de letra.** El motor produce `karaoke.json`; el reproductor web y la
   exportación MP4 lo consumen. La letra se sincroniza una vez y se pinta en dos sitios.
4. **El reproductor web es la experiencia principal.** El MP4 es una exportación.
5. **Local primero y a coste cero.** El portátil del usuario procesa con su GPU y sirve la web.
   La nube es opcional y gratuita si se usa.
6. **Automático, pero corregible.** Siempre se puede arreglar a mano una palabra o un tiempo.
7. **Pocas piezas.** Cada servicio, cola o dependencia debe ganarse su sitio.
8. **Licencias limpias.** Repo MIT público: preferir dependencias y modelos Apache/MIT/BSD;
   NC, AGPL o GPL solo como opción aislada y documentada.

## 4. Experiencia objetivo

- **Fiesta en casa.** El portátil va a la tele por HDMI con el reproductor en modo TV. Los invitados
  escanean un QR con el móvil, buscan canciones y las ponen en cola. Desde el móvil se controla la
  voz guía, el tono y la pausa.
- **Solo con el móvil.** Abrir la biblioteca y cantar con auriculares o un altavoz Bluetooth, con
  la latencia compensada.
- **Crear un karaoke.** Subir una canción (audio o vídeo) o un enlace, elegir idioma (gallego por
  defecto) y pegar la letra si se tiene. En pocos minutos está lista. Si algo no cuadra, se corrige
  en el editor en segundos.
- **Compartir.** Exportar MP4: 16:9 para la tele o YouTube y 9:16 para redes.

## 5. Arquitectura objetivo

```
 entrada: audio/vídeo o enlace · idioma (gl por defecto) · letra opcional
        │
        ▼
 ┌──────────────── MOTOR (Python, GPU del portátil) ────────────────┐
 │ ingesta → separación → [transcripción] → alineación → líneas →   │
 │ paquete de karaoke                                                │
 └───────────────────────────────────────────────────────────────────┘
        │  paquete = karaoke.json + instrumental + voz guía + fondo + portada
        ▼
 ┌──── SERVIDOR (API + cola de trabajos + biblioteca + archivos) ────┐
 └───────────────────────────────────────────────────────────────────┘
        │ HTTP + WebSocket/SSE                       │
        ▼                                            ▼
 REPRODUCTOR WEB (móvil · portátil · TV)       EXPORTACIÓN MP4
 letra animada + motor de audio                ASS animado + ffmpeg/libass (+NVENC)
 editor de sincronía · mando desde el móvil
```

Decisiones iniciales:

| Tema | Decisión inicial | Por qué | Dueña |
|---|---|---|---|
| Unidad de verdad | `karaoke.json` versionado (§6) | coherencia entre web y MP4 | C1 (esquema), C4 (contenido) |
| Experiencia principal | reproductor web; el MP4 es exportación | sirve igual en móvil, portátil y tele; temas y correcciones sin re-renderizar | C7 |
| Dónde se ejecuta | local primero: el portátil procesa y sirve en la red de casa; acceso de fuera con túnel gratuito; nube opcional | 0 €, GPU propia | C8 |
| Lenguajes | Python 3.12 (motor, servidor) y TypeScript (web) | ecosistema ML y navegador | C1 |
| Herramientas Python | uv (workspace), ruff, tipos estrictos en código nuevo, pytest | estándar actual | C1 |
| Servidor | FastAPI con OpenAPI y cliente TS generado; sustituye a Flask | contrato tipado entre back y front; progreso en vivo | C1, C8 |
| Cola de trabajos | la más simple que sirva para una GPU (sin Celery/Redis si no hacen falta) | menos piezas | C8 |
| Base de datos | SQLite por defecto con SQLAlchemy + Alembic (compatible con Postgres) | local primero | C8 |
| Frontend | SvelteKit (salida estática, PWA) + TypeScript | ligero en móviles y teles, bueno para animación | C1, C7 |
| Vídeo | ASS generado en Python + ffmpeg/libass, NVENC si hay; fuera MoviePy, PIL e ImageMagick | rápido y con tipografía correcta | C5 (ASS), C6 (vídeo) |
| Modelos | se eligen con el banco | principio 2 | C3, C4 |
| Código viejo | se aparta (p. ej. `legacy/`) y se borra cuando su sustituto funcione | sitio limpio sin romper nada | C1, C9 |
| Docker | desarrollo nativo en WSL con GPU; Docker solo para desplegar si aporta | menos fricción con 4 GB de VRAM | C1, C8 |

## 6. Contratos compartidos

C1 crea la versión 0 en código (modelos pydantic, JSON Schema, tipos TS generados, validador y
tests) junto con un paquete de ejemplo sintético para que C5 y C7 puedan empezar sin el motor.
Cualquier cambio posterior: decisión escrita + versión del esquema + aviso en `ESTADO.md`.

### 6.1 Paquete de karaoke (una carpeta por canción)

```
<id>/
  karaoke.json      # documento de letra sincronizada
  instrumental.*    # sin voz principal, volumen normalizado
  vocals.*          # voz guía
  background.*      # opcional, apto para web
  cover.jpg         # portada / miniatura
```

Formatos exactos: C3 (audio) y C6 (vídeo).

### 6.2 `karaoke.json` (borrador; C1 lo formaliza)

```json
{
  "schema_version": "1.0.0",
  "id": "…",
  "title": "…", "artist": "…",
  "language": "gl",
  "duration": 215.3,
  "audio": { "instrumental": "instrumental.m4a", "vocals": "vocals.m4a", "loudness_lufs": -14.0 },
  "video": { "background": "background.mp4" },
  "singers": [ { "id": "s1", "name": null, "color": null } ],
  "lines": [
    {
      "id": "l1", "start": 12.30, "end": 15.80, "singer": "s1",
      "words": [
        {
          "text": "Ola", "start": 12.30, "end": 12.62, "confidence": 0.93,
          "parts": [ { "text": "O", "start": 12.30, "end": 12.41 },
                     { "text": "la", "start": 12.41, "end": 12.62 } ]
        }
      ]
    }
  ],
  "provenance": {
    "lyrics_source": "user | asr | lrclib",
    "separation_model": "…", "asr_model": "…", "align_model": "…",
    "engine_version": "…", "language_fallbacks": []
  },
  "edited": false
}
```

Reglas: tiempos en segundos respecto al audio. `parts` es opcional: subunidades de la palabra
(sílabas o grupos de letras) con tiempo real si el alineador lo da. `confidence` (0–1) sirve al
editor para señalar dudas. `text` es lo que se muestra, con la ortografía original (también la
reintegracionista o dialectal); la normalización para alinear es interna. Versionado semántico:
los consumidores aceptan versiones menores nuevas.

### 6.3 Tema visual (`theme.json`)

Tokens compartidos por los dos renderizadores: fuente, tamaños relativos, colores (cantado, por
cantar, contorno, sombra), estilo de animación, líneas visibles, posición, cuenta atrás. Dueña: C5.

### 6.4 Reloj de reproducción (web)

El componente de letra (C5) no reproduce audio: recibe una función `now()` que devuelve los
segundos del audio ya con la latencia compensada, la proporciona el motor de audio (C3) y la
conecta el reproductor (C7). C1 define el tipo TS.

### 6.5 Pasos del motor y CLI

C1 define las interfaces de los pasos (protocolos de Python, p. ej. `Separator`, `Transcriber`,
`Aligner`, `Segmenter`, con sus tipos de entrada y salida) para que el banco (C2) pueda probar
cualquier combinación y C3/C4 las implementen. CLI orientativa (una por paquete; ver
`decisiones/001`):

```
karaoke make <entrada> [--lang gl] [--lyrics letra.txt] [--out dir]   → paquete
karaoke render <paquete> [--theme x] [--aspect 16:9|9:16]             → mp4
karaoke-bench [--set gl] [--compare baseline]                          → informe
```

Ya existen `karaoke validate` y `karaoke demo` (C1).

### 6.6 API

REST + WebSocket o SSE para progreso, descrita en OpenAPI; el cliente TS se genera. Dueña: C8.

## 7. Pistas de la investigación (28/10/2026)

Punto de partida para cada conversación; comprobar versiones y licencias antes de usar.

- **Separación.** [audio-separator](https://pypi.org/project/audio-separator/) 0.47.1
  (19/10/2026) con BS-RoFormer o Mel-Band RoFormer, que lideran
  [MVSEP](https://mvsep.com/quality_checker/synth_leaderboard?ensemble=0); hay modelos karaoke
  que separan voz principal y coros (MVSEP, 2026.10). Demucs está en mantenimiento.
- **Transcripción en gallego.**
  [proxectonos/whisper-large-v3-turbo-gl-v1.0](https://huggingface.co/proxectonos/whisper-large-v3-turbo-gl-v1.0)
  (13/05/2026, Apache-2.0, WER 7,95–9,62 % en habla, sin datos de canto; convertible a
  CTranslate2 para faster-whisper 1.2.1);
  [HiTZ/whisper-large-v3-gl](https://huggingface.co/HiTZ/whisper-large-v3-gl);
  [BSC-LT/whisper-large-v3-LoS](https://huggingface.co/BSC-LT/whisper-large-v3-LoS) (es/ca/gl/eu).
  Otros idiomas: Whisper large-v3-turbo. Probar VAD (Silero) sobre la voz separada contra
  alucinaciones.
- **Alineación.** [WhisperX](https://github.com/m-bain/whisperX) 3.8.6 usa un alineador propio
  (no depende de `torchaudio.functional.forced_align`, retirado en torchaudio 2.9), admite un
  modelo de Hugging Face a medida y devuelve tiempos por carácter; su modelo gallego por defecto es
  `ifrz/wav2vec2-large-xlsr-galician` (2021). Candidatos gallegos de Proxecto Nós:
  `Nos_ASR-wav2vec2-xls-r-300m-gl` (07/2026), `w2v-bert-2.0-gl` (08/2026),
  [`stt_gl_conformer_ctc_large_v1.0`](https://huggingface.co/proxectonos/stt_gl_conformer_ctc_large_v1.0)
  (NeMo; 47 ms de error medio de frontera en habla) y `Nos_ASR-wav2vec2-large-xlsr-53-gl-with-lm`.
  MMS de Meta cubre más de 1000 idiomas, pero MMS-FA es CC-BY-NC.
- **Sílabas o subunidades.** `pyphen` es guionado tipográfico, no sílabas cantadas.
  [pycotovia](https://github.com/TigreGotico/pycotovia) (G2P gallego y español basado en Cotovía,
  Apache-2.0, alfa 0.6.0a1, Python ≥ 3.11);
  [gl-syllabler](https://github.com/bertez/gl-syllabler) (JS). Alternativa sin sílabas: relleno
  continuo con los tiempos por carácter del alineador.
- **Letras.** LRCLIB (base abierta de letras sincronizadas) para idiomas con cobertura; en gallego
  la fuente principal será la letra pegada o la transcripción.
- **Render.** ASS con `\kf` (centésimas; desplazamientos secuenciales), PyonFX 0.11 para efectos,
  libass con HarfBuzz, NVENC en la RTX 3050. Inspiración web:
  [AMLL](https://github.com/amll-dev/applemusic-like-lyrics) (estilo Apple Music; AGPL, solo como
  referencia).
- **Proyecto parecido.** [nomadkaraoke/karaoke-gen](https://github.com/nomadkaraoke/karaoke-gen):
  audio-separator + transcripción + revisión humana + ASS.
- **Datos de prueba.** JamendoLyrics MultiLang / Jam-ALT
  ([paper](https://arxiv.org/abs/2306.07744), 79 canciones CC en en/es/fr/de con tiempos por
  palabra). Para gallego con licencia CC: Jamendo, Internet Archive y Wikimedia Commons; no hay
  tiempos publicados, hay que crearlos y validarlos de oído.

## 8. Reparto en conversaciones

| Conv. | Área | Misión | Dueña de |
|---|---|---|---|
| C1 | Arquitectura, repo y cimientos | dejar el terreno listo para trabajar en paralelo sin pisarse | estructura, herramientas, CI base, contratos v0, CLAUDE.md, git |
| C2 | Banco de pruebas y métricas | medir con números transcripción, sincronía y velocidad | conjuntos de prueba, métricas, runner, skill `probar-karaoke` |
| C3 | Audio: separación y sonido | mejor separación en 4 GB y sonido que funcione en todo | ingesta de audio, separación, normalización, formatos, motor de audio web |
| C4 | Transcripción y sincronización | letra correcta y tiempos reales, gallego primero | idioma, normalización de letra, ASR, alineación, líneas, subunidades |
| C5 | Subtítulos animados | letra bonita y en sincronía, igual en web y MP4 | diseño del movimiento, temas, componente de letra web, generador ASS |
| C6 | Vídeo | fondos y exportación MP4 rápida | fondos, vídeo para web, exportación, portadas |
| C7 | Frontend | app cuidada en móvil, portátil y tele | app web, modo TV, modo fiesta, editor, PWA, i18n |
| C8 | Backend, servidor y despliegue | servidor sencillo que procesa en casa y sirve en todas partes | API, cola, biblioteca, acceso, red, arranque, despliegue |
| C9 | Calidad de código | coherente, limpio, tipado, probado y sin restos | auditoría transversal, borrado de lo viejo |
| C10 | Proyecto profesional | repo open source serio | README, documentación, releases, licencias, comunidad |

La mejora del código va al final porque casi todo el código viejo se sustituye: limpiarlo antes
sería trabajo tirado. Las reglas de calidad se fijan desde C1 y cada conversación las cumple.

## 9. Orden y dependencias

```
Ola 1:  C1 ─────────────┐
Ola 2:  C2 (banco)      │  C5 y C7 pueden empezar ya con el paquete de ejemplo de C1
Ola 3:  C3 → C4         │
Ola 4:  C6 (tras el ASS de C5) · C8 (tras la CLI del motor) · C5/C7 se integran con lo real
Ola 5:  C9 → C10
```

- Hasta que C1 termine, una sola conversación a la vez y sin worktrees (`docs/` aún no se versiona).
- Después, como mucho dos conversaciones a la vez, cada una en su rama y su worktree.
- Una conversación puede necesitar varias sesiones: se retoma con el mismo prompt y `ESTADO.md`.

## 10. Mecanismos de coherencia

- **`ESTADO.md`**: tablero con una fila por conversación (estado, rama, último hito, interfaces que
  expone, pendiente para otras). Se actualiza tras cada hito, no solo al final.
- **`decisiones/NNN-titulo.md`**: decisiones cortas (contexto, decisión, consecuencias, a quién
  afecta). Obligatorias para cambiar algo de este documento o de un contrato.
- **Contratos en código** con fixtures y tests de contrato: cada consumidor valida contra el JSON
  Schema.
- **Ramas** `v3/cN-tema`, PR a `main`, `/code-review` antes de pedir el OK. `main` siempre verde.
- **Banco común** (`probar-karaoke`) con informes fechados en `bench/results/`.
- **Límites de área**: una conversación no edita el área de otra salvo un cambio mínimo
  documentado. Cuando dos áreas se encuentran (p. ej. C5 y C7 en el reproductor), la que llega
  segunda hace la integración y la prueba de extremo a extremo.

## 11. Restricciones

- **Hardware**: RTX 3050 Laptop 4 GB VRAM, Ryzen 7 5800H, 16 GB RAM (WSL ve unos 7–8 GB), SSD
  512 GB. Un modelo en GPU a la vez; int8/float16; modelos descargados una vez y cacheados.
- **Presupuesto**: ~0 €/mes. Nada de APIs de pago por defecto.
- **Claude**: siempre Opus, también en subagentes. Si se acaba la cuota, se espera.
- **Autenticaciones**: si algo necesita login, token o sudo, se para y se pide al usuario, que se
  autentica a mano.
- **Derechos**: el repo no contiene audio con copyright. Las canciones del usuario solo en local;
  las de prueba públicas son CC y se descargan con un script.
- **Privacidad**: todo local; nada se envía a servicios externos sin decirlo.
- **Sin monetización** (decisión firme de julio de 2026, sigue vigente).
- **Git**: commits en inglés con tono humano; nunca commit ni push sin el OK explícito del usuario;
  nunca force-push a `main`.

## 12. Lo que decide cada conversación

Todo lo que no fija este documento: nombres de módulos, librerías concretas, modelos (con datos del
banco), diseño visual, formatos exactos, y si las sílabas se usan o no. Cada conversación hace un
brainstorming corto con el usuario sobre lo específico de su área antes de planificar.

## 13. Acciones del usuario previstas

- **C1**: `sudo apt install ffmpeg` (y lo que haga falta en WSL); `gh auth login` o arreglar el
  token del MCP de GitHub (falla con "Authorization header is badly formatted"); aprobar los MCPs
  recomendados (Context7, Playwright).
- **C2**: cuenta gratuita de Jamendo si su API la pide; validar de oído las referencias en gallego.
- **C3/C4**: token de Hugging Face solo si algún modelo es restringido (p. ej. pyannote para dúos).
- **C7**: probar en su móvil y en su tele.
- **C8**: Tailscale o Cloudflare si quiere acceso desde fuera de casa.
- **C10**: ajustes del repo en GitHub (descripción, temas, protección de rama, releases).
