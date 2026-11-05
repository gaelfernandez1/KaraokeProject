# 010 · Frontend: una app propia, carteles y una fiesta sin instalar nada

- **Fecha**: 30/10/2026
- **Estado**: propuesta (área C7); se aprueba con su PR
- **Afecta a**: C8 (la API que la web espera, HTTPS en casa, Range), C10 (nombre y marca), C3, C5 y
  C6 (la app integra su motor de audio, su letra y su fondo sin cambiarlos)

## Contexto

La web es la experiencia principal (`00-vision.md` §3.4): cantar en el móvil, en el portátil y en la
tele por HDMI, crear karaokes, montar una fiesta con los móviles de mando y corregir la letra. Tenía
que ser rápida en móviles y teles, profesional y con una identidad propia, que no pareciera una
plantilla.

## Qué se miró

- **Cómo se consigue un diseño propio**: los resultados buenos no salen de una plantilla sino de
  fijar antes un sistema (colores con nombre, tipos y su papel, maquetas, principios), contrastarlo
  con lo que saldría por defecto y revisar capturas reales con un criterio separado y exigente
  (calidad, originalidad, oficio y funcionamiento) hasta que no queda nada genérico. Se evitan los
  tics de moda: crema con serif y terracota, negro con un solo acento ácido, tarjetas iguales con
  sombra gris, etiquetas en mayúsculas, Inter o Space Grotesk.
- **Karaoke y fiesta** (KaraFun, Singa, Karaoke Eternal, PiKaraoke, Jackbox, Apple Music Sing,
  Spotify Jam): unirse con QR y nombre en una web; turnos justos y visibles; el anfitrión decide qué
  pueden hacer los invitados; volver a entrar con el mismo nombre; nada de móvil como micrófono
  (poco fiable). Por HDMI un portátil no recibe el mando de la tele: los mandos reales son el móvil,
  el teclado o un pasador. Editor: tocar al ritmo por palabra, mover ±10/50 ms, repetir la línea
  (ningún editor revisado lo tiene).
- **Tele** (guías de Apple tvOS, Android TV y Fire TV): márgenes del 5 %, texto de 28 px o más a
  1080p, foco evidente.
- **Técnica** (versiones del 30/10/2026): SvelteKit 3.1 + Svelte 5.57 + Vite 8; el plugin PWA
  habitual no soporta Kit 3; SSE reconecta solo; un mock dentro de cada navegador no sirve para
  que tele y móviles compartan cola.

## Enfoques comparados

| Tema | Elegido | Descartado y por qué |
|---|---|---|
| Dirección visual | **Cartaz**: cada canción es un cartel de verbena o de concierto; el relleno ámbar de la letra es el lenguaje de estado | neón y cristal (el karaoke genérico); textil de fiadeiro (frío para trap y fiesta, poco legible en la tele); reproductor minimalista (anónimo) |
| Framework | SvelteKit 3 SPA estática (ya estaba) | Astro, Next o SolidStart: nada que ganar en una SPA local y habría que rehacer letra y audio |
| Estilos | CSS propio con tokens, `clamp()`, `color-mix` y container queries | Tailwind: empuja a la plantilla y no ahorra nada con estilos con ámbito |
| Idiomas | diccionario tipado propio; el gallego es la referencia y un test exige las mismas claves | Paraglide 2: recarga al cambiar de idioma (cortaría la canción) y descarga su plugin al compilar |
| En vivo | SSE con el estado completo y versión, y órdenes por POST | WebSocket: más piezas sin necesidad; WebRTC entre móviles: frágil |
| Turnos | función pura en la web (`rotation.ts`) que todas las pantallas calculan igual | turnos en el servidor: habría que escribirlos dos veces |
| Servidor de desarrollo | simulado en un middleware de Vite, con los paquetes reales | MSW: un estado por navegador |
| Sin conexión | service worker propio; canciones guardadas en Cache Storage con respuestas Range | `@vite-pwa/sveltekit`: no soporta Kit 3 |
| QR | `lean-qr` (MIT, 4 kB) | librerías más grandes |

## Decisión

- **Sistema de diseño**: solo oscuro; azul noche `#16122E` (no negro), papel `#F3EFFA`, ámbar
  `#FFC531` (lo cantado), fucsia escaso, y los colores de cantante, que en la fiesta son personas.
  Big Shoulders (carteles, títulos, el código de la sala) y Atkinson Hyperlegible Next (texto), OFL
  y autoalojadas. Un único momento animado: la marca «se canta» al abrir. Guía viva en `/estilo`.
- **Pantallas**: `/` (pared de carteles), `/crear`, `/cantar/<id>`, `/editar/<id>`, `/festa` (tele),
  `/festa/<código>` (móvil) y `/axustes`. Detalle en `docs/web.md`.
- **Nombre provisional «Foliada»**, en una constante (`Wordmark.svelte`) para que C10 lo cambie.
- **Integración sin tocar otras áreas**: `<Lyrics>` (C5), `AudioEngine` (C3) y `BackgroundSync` (C6)
  se usan tal cual; `/proba-audio` se retira (la sustituyen el reproductor y Axustes) y
  `/proba-letra` queda solo en desarrollo.

## API que la web espera (para C8)

La web encapsula el cliente en `#lib/api` y `#lib/party`; cuando C8 publique su OpenAPI se generan
los tipos (`openapi-typescript`). Mientras, la forma es la del servidor simulado
(`web/dev/mock/plugin.ts`), que C8 puede cambiar avisando:

- `GET /api/songs` → resúmenes (`id`, `title`, `artist`, `language`, `duration`, `cover`,
  `has_video`, `created_at`, `edited`, `lyrics_source`, `hook`: la línea principal más repetida o,
  si no hay repetidas, la primera de tres palabras o más).
- `GET /media/{id}/{fichero}` → ficheros del paquete, `karaoke.json` incluido, con peticiones Range.
- `PUT /api/songs/{id}/doc` → guarda la letra corregida (valida y marca `edited: true`).
  `DELETE /api/songs/{id}`.
- `POST /api/jobs` (multipart: `file` o `url`, `language`, `lyrics?`, `lrclib?`, `title?`,
  `artist?`) → trabajo (`id`, `kind`, `title`, `stage`, `progress` de la fase, `song_id`, `file`,
  `error`, `with_lyrics`, `created_at`); `GET /api/jobs`; `GET /api/jobs/{id}/events` (SSE `job`);
  `DELETE /api/jobs/{id}` cancela. Fases: `queued`, `download`, `separate`, `transcribe`, `align`,
  `audio`, `video`, `done`, `error`, `cancelled`.
- `POST /api/songs/{id}/exports` (`aspect`, `theme`) → trabajo de vídeo; al acabar, `file` es el MP4
  dentro del paquete.
- Fiesta: `POST /api/parties` → `{code, host_token}`; `GET /api/parties/{code}`;
  `GET …/events?token=` (SSE `state` con el estado completo y `version`, al conectar y tras cada
  cambio; `command` solo a la tele); `POST …/guests {name}` (mismo nombre = mismo invitado y token);
  `POST …/queue {song_id}`; `DELETE …/queue/{item}` (el invitado, las suyas; la tele, cualquiera);
  `POST …/promote/{item}`; `PUT …/advance {item_id, state}`; `POST …/commands` (de la tele siempre;
  de los invitados si `guests_control`); `PUT …/playback`; `PUT …/settings`. Credencial en
  `Authorization: Bearer` (en SSE, `?token=`).
- `GET /api/server` → `{url}` con la dirección de la red de casa para el QR.

## Resultados

- **Diseño revisado con capturas en varias rondas**: un revisor independiente puntuó cada ronda
  (calidad, originalidad, oficio, funcionamiento) con capturas de móvil, portátil y tele, y cada
  defecto se corrigió y, si era comprobable, quedó en una prueba (desbordes a 360 y 390 px, vistas
  previas sin recortar). Lo que más cambió por esas rondas: el cartel acompaña a la canción hasta el
  reproductor (vídeo y portada impresos a dos tintas sobre su papel, o la «versión nocturna» del
  cartel), la tele dice siempre quién canta y tiene controles a la vista, el ámbar dejó de ser
  color de persona y de papel, y los móviles de los invitados ganaron una entrada con su color,
  una lista con recortes del cartel y un mando que dice cuándo les toca.
- **Pruebas**: lógica en Vitest (unos 290 tests: turnos, tele anfitriona frente a saltos y cargas
  lentas, editor con 300 operaciones aleatorias, cliente, conexión, i18n, simulador, rangos…) y de
  navegador en móvil, portátil y tele (biblioteca, reproductor, crear, fiesta con una tele y dos
  móviles, editor, ajustes, desbordes y axe sin fallos graves de accesibilidad).
- **Peso**: JavaScript comprimido de una visita en frío: unos 70 kB la biblioteca y crear, 92 kB el
  reproductor y 98 kB la tele de la fiesta (presupuesto: 120–150 kB; `pnpm perf`).
- **Sin conexión** comprobado en Chromium: la app abre sin red, una canción guardada suena y su
  vídeo salta.

## Consecuencias

- **C8**: implementar la API de arriba; servir los vídeos con Range; **HTTPS en la red de casa**:
  por `http://<ip>` los móviles no tienen modo sin conexión, cambio de tono, pantalla encendida ni
  portapapeles (en la tele, que usa `localhost`, todo funciona); anunciar en `/api/server` la IP
  que alcanzan los móviles (en WSL, la de Windows).
- **C10**: decidir nombre y marca con el usuario (el icono es la «F» de la marca medio cantada).
- **C6**: la web imprime el vídeo y la portada a dos tintas sobre el papel del cartel; el MP4 sigue
  con el vídeo a color. Si se quiere que coincidan, `karaoke render` puede aplicar el mismo
  tratamiento con filtros de ffmpeg (escala de grises y multiplicar sobre el color del papel).
- **C8** (fiesta): quien está cantando puede mandar sobre su propia canción aunque el anfitrión no
  haya abierto el mando a todos (así lo hace el simulador).
- **Usuario**: probar en su móvil, su portátil y su tele (pendiente).
