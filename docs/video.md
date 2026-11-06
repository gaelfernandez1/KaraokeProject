# Video

Song backgrounds and MP4 export with the animated lyrics. The decisions are in
[`plan-v3/decisiones/008-video.md`](plan-v3/decisiones/008-video.md) (in Spanish); the timings, in
`bench/results/2026-10-30-c6-render/`.

## A package's background

`karaoke make` keeps what the song brings for the picture:

- **`background.mp4`** if the file has video (a music video from YouTube, for example): H.264 that
  any phone or TV plays, at most 1280×720 and 30 fps, one keyframe per second (seeking is instant),
  the index at the start and no audio. It goes in `video.background`.
- **`cover.jpg`**: the embedded artwork if there is one (mp3, m4a) or, if not, a frame a third of
  the way into the video. It goes in `cover`.

For a package already made (or to change its background):

```bash
uv run karaoke background <package> <video, song with artwork, or image>
```

Code: `karaoke_engine.video.media` (`probe_video`, `extract_background`, `extract_cover`,
`add_background`, `mean_luma`).

## Exporting the MP4

```bash
uv run karaoke render <package> [--theme clasico] [--aspect 16:9|9:16] [--background auto]
                                [--vocals 0.3] [--dim 0.8] [--size 1280x720] [-o video.mp4]
```

- **Background** (`--background`): `auto` uses the package's video, otherwise its cover and
  otherwise a gradient in the theme's colours; also `video`, `cover`, `gradient` or the path to a
  video or an image. A background with the video's shape fills it; with another shape it is shown
  whole over an enlarged, blurred and darker copy, never stretched or cropped. In 9:16 it moves up to
  leave the lyrics below. An image moves very slowly.
- **Legibility**: the background is darkened according to its brightness (`--dim` sets it by hand:
  1 means no darkening) and a dark gradient band goes behind the lyrics.
- **Lyrics**: the ASS of the subtitles ([`subtitles.md`](subtitles.md)) with the same layout as the
  web app, plus the **title and artist** at the start (if the first line comes 4 s or more in) and
  **credits** at the end (title, artist and the first paragraph of `LICENSE`, if 4 s or more are
  left).
- **Audio**: the instrumental as is; with `--vocals`, mixed with the guide vocals at that level.
- **Thumbnail**: next to the video, a 1280 px `.jpg` with the title over the background.
- **Encoding**: NVENC on the GPU and, if that is not possible, x264.

A 4-minute song takes 27–45 s on the RTX 3050 with a video or gradient background, and about a
minute with a cover image.

Code: `karaoke_engine.video.render` (`render`, `title_events`, `credits_text`),
`karaoke_engine.video.graph` (the background's filter graph) and `karaoke_engine.video.encode`.

## In the web app

`BackgroundSync` (`web/src/lib/video/background.ts`) keeps a muted `<video>` in step with the audio:
it starts and stops it with the clock, jumps if it drifts more than 0.3 s and, between 40 ms and
0.3 s, speeds it up or slows it down by 5 % at most until it catches up. If the video is shorter than
the song, it loops.

```ts
const sync = new BackgroundSync(videoElement, { now: () => engine.now(), get playing() { return engine.playing; } });
// on every frame:
sync.tick();
```

`/proba-letra` shows it with the background as in the MP4 (a blurred cover behind, the whole video,
darkened, a band under the lyrics). Both the development server and the real one serve videos with
Range requests, without which a browser cannot seek in a video.

## Tests

```bash
uv run pytest packages/engine/tests/test_video_*.py packages/engine/tests/test_make.py
pnpm --dir web test                 # BackgroundSync
pnpm --dir web test:e2e             # the background video follows the clock (Chromium)
```
