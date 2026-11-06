# The web app

The app in `web/` (SvelteKit 3, Svelte 5, TypeScript) is the main way to use the karaoke: the
library, the player, creating karaokes, the party with the TV and the phones, the lyrics editor and
the settings. It works the same on a phone, a laptop and a TV over HDMI. The interface is in
Galician (the default), Spanish and English, so the screens and routes below keep their Galician
names. The design decisions are in
[`plan-v3/decisiones/010-frontend.md`](plan-v3/decisiones/010-frontend.md) (in Spanish).

## Running it

```bash
pnpm --dir web dev            # http://localhost:5173, with the stand-in server
pnpm --dir web dev --host     # also for phones on the home network
```

In normal use, the server serves the built app (`make serve`, see [`server.md`](server.md)). For
development, `pnpm dev` brings a stand-in server (`web/dev/mock/`) with the same `/api` and `/media`
routes; with `KARAOKE_SERVER=http://127.0.0.1:8765 pnpm --dir web dev` it talks to the real server
instead (from the laptop itself: through the proxy, a phone counts as coming from outside). The
stand-in has:

- **Library**: the package folders in `fixtures/packages/` and `bench/data/paquetes/` (or those in
  `KARAOKE_PACKAGES`, separated by `:`). The editor's corrections are kept in memory: the packages
  are never touched.
- **Create**: jobs go through the engine's stages in about 12 s (`KARAOKE_MOCK_JOB_SECONDS`) and add
  a song that reuses the audio of `demo-sintetico`.
- **Party**: rooms in memory, with live events (SSE).

The examples' audio is not versioned: `uv run karaoke demo fixtures/packages/demo-sintetico` makes
the demo's, and the end of each `LICENSE` says how to make the real songs'.

## Screens

| Route | Screen |
|---|---|
| `/` | **Cancións**: the wall of posters, with search (ignoring accents and case) and a language filter. `/` focuses the search box. |
| `/crear` | **Crear karaoke**: a file or a link, the language (Galician by default), optional lyrics or LRCLIB; jobs are followed live from any screen (a ring on «Crear»). |
| `/cantar/<id>` | **Reprodutor**: a full-screen stage (video, cover or the poster's colour) with the lyrics; the «Son» panel has guide vocals, pitch, delay, lyrics style, downloads and video. `?t=12.3` freezes the lyrics without sound (for screenshots and tests). |
| `/editar/<id>` | **Editor**: correct words and timings, listen to a line or loop it, tap the rhythm with the space bar. |
| `/festa` | **Festa (TV)**: code, QR code, the queue by turns, an «Agora canta» poster with a countdown, and the song. |
| `/festa/<code>` | **Remote (phone)**: join with a name, ask for songs, see the queue and control the player if the host allows it. |
| `/axustes` | **Axustes**: language, lyrics style, default guide vocals and this device's delay calibration. |
| `/estilo` | Living style guide (development only). |
| `/proba-letra` | Lyrics test page (development only; its browser tests use it). |

## Keyboard

| Where | Keys |
|---|---|
| Player and TV | Space or K: play or pause · ← →: 5 s · Shift + ← →: previous or next line · ↑ ↓: guide vocals · − +: pitch · F: full screen · Esc: leave |
| TV, between songs | Enter: start now · arrows: move between the buttons |
| Editor | ← →: word · ↑ ↓: line · [ ]: start ±10 ms (Shift, 50 ms) · , .: end · Space: listen · L: loop · T: tap the rhythm · Enter: correct the text · Ctrl Z: undo · Ctrl S: save |

Media keys (and presentation clickers) also work in the player, and the phone's lock screen shows
the song (Media Session).

## The party

1. The laptop opens `/festa` on the TV and presses «Comezar a festa». After a reload, it offers to
   carry on with the same party.
2. Guests scan the QR code (or type the code) and join with their name. Each gets a colour (the
   singers' colours): on the TV and the phones, the colour is the person. Joining again with the
   same name gets the same guest back.
3. **Turns**: whoever has sung least goes first; within each round, in order of arrival
   (`web/src/lib/party/rotation.ts`). That way nobody takes over the TV by asking for ten songs.
4. Between songs, the TV announces who sings with a 10 s countdown (Enter starts it at once).
5. The phones act as a remote (pause, skip, guide vocals, pitch) only if the host allows it.

The queue lives on the server; every screen works out the turns with the same function.

## Installing and singing offline

The app can be installed (manifest and icons in `web/static/`) and has its own service worker
(`web/src/service-worker/`): it keeps the interface so it opens without a network and, in the
player's «Son» panel, «Gardar sen conexión» downloads the whole song (lyrics, audio, cover and video)
to the device. Saved songs show a marked corner and a «Gardadas» filter in the library, and are
managed in Axustes. A new version of the app waits until «Actualizar» is pressed: it never cuts a
song short.

It needs HTTPS (or `localhost`): through `http://<ip>` there is no service worker and the option
does not appear.

## Design

- **Posters**: every song is a village-festival or concert poster (the cover in two inks on
  printing paper: kraft, tomato, white, lilac, festival blue or night; the title in the condensed
  face as big as it fits; without a cover, it quotes the chorus). The paper and the arrangement come
  from the song's id, so a poster is always the same, in the library, when the song opens, behind the
  player (covers are printed the same way) and on the party TV.
- **"Sung" is the state**: the lyrics' amber (`--farol`) fills from left to right the progress of a
  karaoke being made, the current tab or the position bar, which draws the song's shape (where it is
  sung).
- **Colour is a person** at a party (orange, cyan, pink and green); amber is never a person nor a
  poster paper.
- Dark mode only (it is used at night and on a TV). The tokens are in
  `web/src/lib/ui/styles/tokens.css`.
- Shapes: what is paper (posters, rows, cards) is square; controls, 10 px; pills only for filters and
  a person's name. Figures are set in the poster face (the text face draws a slashed zero).
- Type: Big Shoulders (posters and titles) and Atkinson Hyperlegible Next (text), self-hosted and
  cut down to Latin with `scripts/build_web_fonts.py` (the OFL licence next to each).
- TV: everything within the 5 % title-safe margin on each side, text of 28 px or more at 1080p, a
  6 px white focus ring. While someone sings, their name goes at the top in their colour and a line
  in their colour moves along the bottom with the song.
- Method: every visual change is reviewed with screenshots on a phone, a laptop and a TV
  (`web/dev/shots.mjs`) against these rules.

## Languages

`web/src/lib/i18n/gl.ts` is the reference dictionary; `es.ts` and `en.ts` must have the same keys (a
test checks it). Galician is the default for any browser in Galician, Spanish, Portuguese, Catalan,
Basque or Asturian; English for the rest that speak English. It changes in Axustes without
reloading, so a song is never cut short.

## Tests

```bash
pnpm --dir web test       # logic: turns, editor, client, i18n, the stand-in server…
pnpm --dir web test:e2e   # browser: phone, laptop and TV, with axe (accessibility)
pnpm --dir web test:e2e:server   # browser against the real server with the fake engine
pnpm --dir web build && pnpm --dir web perf   # JavaScript budget per screen
node web/dev/shots.mjs /cantar/demo-sintetico --sizes phone,laptop,tv   # screenshots
```

The browser tests need Playwright's Chromium and, on WSL without root, `LD_LIBRARY_PATH` pointing at
`libnss3` (see [`subtitles.md`](subtitles.md)).

The README's images come from two scripts: `web/dev/brand.mjs` (banners and social preview) and
`web/dev/readme-media.mjs` (screenshots and the animation, from the real server with the demo
song).

## Known limits

- **HTTPS at home**: through `http://<laptop-ip>` phones get no offline mode, no pitch shifting
  (AudioWorklet), no screen kept on and no clipboard. On the TV (`localhost`) everything works.
  Through Tailscale (HTTPS, [`server.md`](server.md)) too; a certificate for the home IP address is
  still pending.
- **iPhone**: it only puts `<video>` elements in full screen; installed on the home screen it does
  take the whole screen.
- **WSL**: the development server announces WSL's internal IP address in the QR code; with
  `networkingMode=mirrored` and the firewall rule (see [`server.md`](server.md)) phones reach the
  laptop.
