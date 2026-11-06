# Animated lyrics

How the lyrics of a `karaoke.json` are drawn, the same in the web player and in the MP4. The
decisions and what was discarded are in
[`plan-v3/decisiones/007-subtitulos.md`](plan-v3/decisiones/007-subtitulos.md) (in Spanish).

## The idea

What decides **what is seen and when** (which row each line goes in, where it breaks, at which size,
when it comes in and out, the countdown) is a single layout algorithm with two identical copies:

- `karaoke_engine.subtitles.layout` (Python), the reference, used by the MP4;
- `web/src/lib/lyrics/layout.ts`, the same logic for the browser.

Both measure text with the same table of font widths (`*.metrics.json`), so they break lines in the
same places in any browser and in the video. The shared cases in `fixtures/lyrics-layout/` force
them to give the same result (with a 1e-6 tolerance): a Python test fails if they are stale, and a
web test fails if the web does not match.

What decides **how each row is painted** is done by each renderer with its own tool:

- the web, with the DOM: two copies of the text per row, the one below "to sing" and the one on top
  "sung", clipped (`clip-path`) up to the edge of the wipe;
- the MP4, with ASS events that libass draws: `\kf` per syllable (wipe) or `\k` per word.

Measured side by side, the web and libass agree within 1–3 px (`scripts/side_by_side.py`).

## What is shown

- **Pages** (`layout.mode = "pages"`, the classic one): `visible_lines` fixed rows that take turns.
  While a line is sung, the next one is already written in the other row; when a line ends
  (+`hold`), its place is taken by the line `visible_lines` places later, always at least 0.5 s
  before it is sung. The text does not move while it is being read.
- **Scrolling** (`"scroll"`, the modern one): the line being sung stays at the anchor (42 % of the
  height with `position = "center"`), the previous one dimmed above and the next ones below, fainter
  the further away. The list moves up in `transition` seconds and stops 0.25 s before the next line.
- **Blocks and breaks**: a gap of `countdown_min_gap` seconds (5) between lines splits the song into
  blocks. A block appears `lead_in` seconds (3) before it is sung, with a **countdown** of
  `countdown_dots` dots that go out from right to left, one every `countdown_step` seconds, above the
  start of the first line. In breaks of `break_bar_min` seconds (8) or more, a **bar** shows how long
  is left (pages only).
- **Wipe**: each syllable (`parts`), or each word without parts, fills from left to right at its real
  time; between words, it waits. With `fill = "word"`, each word switches at once when it starts.
  Everything runs `anticipation` seconds (0.05) ahead of the sound: a late letter is much more
  noticeable than an early one, and this makes up for the frame it takes to paint.
- **Backing vocals** (`role = "backing"`): smaller (`backing.scale`), in brackets and somewhat
  transparent, in a row under the lead line they sound with (the one they overlap most, or the
  previous one if it ended less than 1.5 s before); with none nearby, they go alone.
- **Singers**: with two or more, each fills with their colour (`singer.color` or the theme's
  `colors.singers` palette).
- **Breaks**: a line that does not fit is split into two balanced rows, preferably after a comma or
  a full stop; if it still does not fit, it shrinks (down to 0.6).
- **Size**: `font_size` × the screen's height, but no more than what leaves `min_row_chars` letters
  per row in the usable width; `margin` (5 %) on each side.

## Themes

The themes and their fonts are in `packages/engine/src/karaoke_engine/subtitles/themes/` (a single
copy: the web app imports them from there).

| id | Mode | Font | Look |
|---|---|---|---|
| `clasico` | pages | Nunito Black | white with a dark outline, sung in yellow, shadow |
| `moderno` | scrolling | Inter ExtraBold | faint white to sing, full white when sung, soft glow |
| `contraste` | pages | Atkinson Hyperlegible Next ExtraBold | yellow on a black box, bigger, word by word |

To add one, copy a `.json`, change `id` and `name` and adjust the values (the schema is
`schemas/theme.schema.json`). For another font, add it to `FONTS` in `scripts/build_fonts.py`, run
`uv run --with fonttools --with brotli python scripts/build_fonts.py` and add it to
`web/src/lib/lyrics/themes.ts` too. The fonts come with their OFL licence and their origin in
`themes/fonts/README.md`.

## Web

```svelte
<script>
	import { Lyrics, THEMES, normalizeDoc } from '#lib/lyrics';
</script>

<Lyrics doc={normalizeDoc(doc)} theme={THEMES.clasico} clock={engine} />
```

`clock` is any `PlaybackClock`: the `AudioEngine` from `#lib/audio/engine.js`, which already takes
off the output latency. The component fills its container (`position: absolute; inset: 0`) and
adapts to its size. Each frame only writes opacities, the edge of the wipe and the list's offset:
with a phone's CPU simulated 4 times slower, the median and p99 are 16.7 ms per frame, none above
20 ms.

Test page: `pnpm --dir web dev` and `/proba-letra` (choose a song, a theme and a screen size, and
play with audio). `?t=12.3` freezes the lyrics at that moment and `?fondo=liso` removes the
background.

## Video

```bash
uv run karaoke subtitles <package> [--theme clasico] [--size 1920x1080] [-o lyrics.ass]
uv run karaoke preview <package> [--theme] [--size 1080x1920] [--start 20 --duration 30] [-o p.mp4]
```

`subtitles` writes the ASS; `preview`, a quick MP4 with the lyrics over a plain background, the
instrumental and the guide vocals (to check by eye and ear). To burn the ASS into a video, libass
needs the fonts: `subtitles=lyrics.ass:fontsdir=<themes/fonts>`
(`karaoke_engine.subtitles.themes.fonts_dir()`). From Python: `build_ass(doc, theme, width, height)`.

## Tests

```bash
uv run pytest packages/engine/tests/test_subtitles_*.py      # layout, ASS and a libass frame
pnpm --dir web test                                           # TS layout (shared cases), scene, wipe
pnpm --dir web exec playwright install chromium --only-shell  # once
pnpm --dir web test:e2e                                       # the component in Chromium: phone, laptop and TV
uv run python scripts/side_by_side.py fixtures/packages/demo-sintetico --times 4.5,13
```

Chromium needs `libnss3` and `libnspr4`. With administrator rights:
`sudo pnpm --dir web exec playwright install-deps chromium`. Without them, they can be extracted
from Ubuntu's packages into a folder of your own (`apt-get download libnspr4 libnss3` and `dpkg -x`)
and `LD_LIBRARY_PATH` pointed at its `usr/lib/x86_64-linux-gnu`.

After changing the layout on purpose: `uv run python -m karaoke_engine.subtitles.conformance
--write`, and repeat the change in `layout.ts` until `pnpm --dir web test` passes.
