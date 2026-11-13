# The web app

The app in `web/` (SvelteKit 3, Svelte 5, TypeScript) is the main way to use the karaoke: the
library, the player, creating karaokes, the party with the TV and the phones, the lyrics editor and
the settings. It works the same on a phone, a laptop and a TV over HDMI. The interface is in
Galician (the default), Spanish and English, so the screens and routes below keep their Galician
names. The design decisions are in
[`plan-v3/decisiones/010-frontend.md`](plan-v3/decisiones/010-frontend.md) (the app) and
[`plan-v3/decisiones/017-noite.md`](plan-v3/decisiones/017-noite.md) (its look), in Spanish.

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
| `/` | **Main menu**: the night globe of Galicia with Cantar, Festa, Crear and Axustes, then **Cancións**: the songs, with search (ignoring accents and case) and a language filter. `/` focuses the search box; the globe can be stopped (remembered on the device). |
| `/crear` | **Crear karaoke**: a file or a link, the language (Galician by default), optional lyrics or LRCLIB; jobs are followed live from any screen (a ring on «Crear»). |
| `/cantar/<id>` | **Reprodutor**: a full-screen stage (video, cover or the song's own sky of lights) with the lyrics; the «Son» panel has guide vocals, pitch, delay and lyrics style; «Descargar» has the song's karaoke videos (made there, with their progress live, and kept to download any time), the music without vocals, the vocals and the lyrics, all named after the song, and the offline copy. `?t=12.3` freezes the lyrics without sound (for screenshots and tests). |
| `/editar/<id>` | **Editor**: correct words and timings, listen to a line or loop it, tap the rhythm with the space bar. |
| `/festa` | **Festa (TV)**: code, QR code, the queue by turns, an «Agora canta» announcement with a countdown, and the song. |
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
player's «Descargar» panel, «Gardar sen conexión» downloads the whole song (lyrics, audio, cover
and the 720p video, never the full-quality one kept for the export) to the device. Saved songs show a marked corner and a «Gardadas» filter in the library, and are
managed in Axustes. A new version of the app waits until «Actualizar» is pressed: it never cuts a
song short.

It needs HTTPS (or `localhost`): through `http://<ip>` there is no service worker and the option
does not appear.

## Design

- **Galicia at night, on its own planet**: the main menu is a small planet where Galicia is the
  only land, drawn in 3D: its real relief lit by the moon, its coast, the lines between its
  provinces, the lights of its towns as they look from the air (one inhabited patch of about
  0.45 km each, Kontur Population 2023) and the lighthouses of its coast sweeping the sea at their
  real rhythm and range (Wikidata). The whole planet moves as one: it sways slowly, and a visitor
  can take it and turn it; let go, it comes back. The first time in a visit it turns in from the
  open sea and the lights come on, cities first; with reduced motion it is simply there, lit and
  still. A button stops it.
- **One globe for the whole app**: `web/src/lib/globe/Stage.svelte` is a canvas under every
  screen, mounted once in the root layout. A screen says where it wants the globe with
  `GlobeAnchor.svelte` (a square in its own layout) and the globe glides there from wherever it
  was. The globe shows what the screen is about (`stage.mood`): a party (rings of the singers'
  colours and rockets), a karaoke being made (the lights come on from the west as far as the job
  has got), the settings (meridians and contour lines come forward). The engine
  (`web/src/lib/globe/engine.ts`, WebGL 2, no 3D library) and the map load after the first paint,
  only when a screen asks for the globe; the canvas covers just the globe, draws fewer pixels and
  frames on a machine that cannot keep up, waits while the page changes and stops when the globe
  is out of sight. Without WebGL a still outline stays. Rebuild the data with
  `uv run scripts/galicia_map.py`.
- **Colour**: the sea and sky are blue-black; white is for words and for the one main action of
  each screen; the flag's sky blue (`--ceo`) is what is selected or has the focus; the gold of a
  lit window (`--ouro`) is what is on: sung words, what happens now, the lights. At a party each
  person has a colour (pink, mint, coral and lime), never gold or blue. Dark mode only (it is
  used at night and on a TV). The tokens are in `web/src/lib/ui/styles/tokens.css`.
- **Shapes**: everything is rounded: fields and small controls, rows and pictures, panels;
  buttons and people's names are pills. What floats over the globe is a translucent panel
  (`.panel`) that lets the night show through.
- **Songs**: a list with the song the pointer or the focus is on shown big beside it (cover, the
  line everyone knows, facts and what to do with it). A song without a cover gets a sky of its
  own, two soft lights whose colours come from its id, with its first letter
  (`web/src/lib/poster/Cover.svelte`).
- Type: Unbounded (the menu, titles and names), Figtree (text) and Martian Mono (figures that are
  measured or read aloud: times, counts, the room code); self-hosted and cut down to Latin with
  `scripts/build_web_fonts.py` (the OFL licence next to each). Sentence case everywhere.
- TV: everything within the 5 % title-safe margin on each side, text of 28 px or more at 1080p, an
  evident sky-blue focus ring. While someone sings, their name goes at the top in their colour.

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
