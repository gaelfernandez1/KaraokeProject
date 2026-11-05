# Web: la app

La app de `web/` (SvelteKit 3, Svelte 5, TypeScript) es la experiencia principal del karaoke: la
biblioteca, el reproductor, crear karaokes, la fiesta con la tele y los móviles, el editor de
letra y los ajustes. Funciona igual en el móvil, el portátil y la tele por HDMI. La interfaz está
en gallego (por defecto), castellano e inglés.

## Arrancar

```bash
pnpm --dir web dev            # http://localhost:5173, con el servidor simulado
pnpm --dir web dev --host     # también para los móviles de la red de casa
```

Mientras no exista el servidor de verdad, `pnpm dev` trae uno simulado (`web/dev/mock/`) con las
mismas rutas `/api` y `/media` que usará la app:

- **Biblioteca**: las carpetas de paquetes de `fixtures/packages/` y `bench/data/paquetes/` (o las
  de `KARAOKE_PACKAGES`, separadas por `:`). Las correcciones del editor se guardan en memoria:
  nunca se tocan los paquetes.
- **Crear**: los trabajos recorren las fases del motor en unos 12 s
  (`KARAOKE_MOCK_JOB_SECONDS`) y añaden una canción que reutiliza el audio de `demo-sintetico`.
- **Fiesta**: salas en memoria, con eventos en vivo (SSE).

El audio de los ejemplos no se versiona: `uv run karaoke demo fixtures/packages/demo-sintetico`
crea el del demo, y el final de cada `LICENSE` dice cómo crear el de las canciones reales.

## Pantallas

| Ruta | Pantalla |
|---|---|
| `/` | **Cancións**: la pared de carteles, con buscador (sin acentos ni mayúsculas) y filtro de idioma. `/` enfoca el buscador. |
| `/crear` | **Crear karaoke**: archivo o enlace, idioma (gallego por defecto), letra opcional o LRCLIB; los trabajos se siguen en vivo desde cualquier pantalla (anillo en «Crear»). |
| `/cantar/<id>` | **Reprodutor**: escenario a pantalla completa (vídeo, portada o el color del cartel) con la letra; panel «Son» con voz guía, ton, retardo, estilo de la letra, descargas y vídeo. `?t=12.3` congela la letra sin sonido (capturas y pruebas). |
| `/editar/<id>` | **Editor**: corregir palabras y tiempos, escuchar la línea o repetirla en bucle, marcar el ritmo con espacio. |
| `/festa` | **Festa (tele)**: código, QR, cola por turnos, cartel «Agora canta» con cuenta atrás y la canción. |
| `/festa/<código>` | **Mando (móvil)**: entrar con un nombre, pedir canciones, ver la cola y mandar si el anfitrión lo permite. |
| `/axustes` | **Axustes**: idioma, estilo de la letra, voz guía por defecto y calibración del retardo de este aparato. |
| `/estilo` | Guía de estilo viva (solo en desarrollo). |
| `/proba-letra` | Página de prueba de la letra (solo en desarrollo; la usan sus pruebas de navegador). |

## Teclado

| Dónde | Teclas |
|---|---|
| Reproductor y tele | Espacio o K: reproducir o pausar · ← →: 5 s · Mayús. + ← →: línea anterior o siguiente · ↑ ↓: voz guía · − +: tono · F: pantalla completa · Esc: salir |
| Tele, entre canciones | Intro: empezar ya · flechas: moverse por los botones |
| Editor | ← →: palabra · ↑ ↓: línea · [ ]: inicio ±10 ms (Mayús., 50 ms) · , .: final · Espacio: escuchar · L: repetir · T: marcar el ritmo · Intro: corregir el texto · Ctrl Z: deshacer · Ctrl S: guardar |

Las teclas multimedia (y los pasadores de diapositivas) también funcionan en el reproductor, y la
pantalla bloqueada del móvil muestra la canción (Media Session).

## La fiesta

1. El portátil abre `/festa` en la tele y pulsa «Comezar a festa». Si se recarga, ofrece
   continuar la misma fiesta.
2. Los invitados escanean el QR (o escriben el código) y entran con su nombre. Cada uno tiene un
   color (los de los cantantes): en la tele y en los móviles, el color es la persona. Volver a
   entrar con el mismo nombre recupera el mismo invitado.
3. **Turnos**: quien ha cantado menos va antes; dentro de cada vuelta, por orden de llegada
   (`web/src/lib/party/rotation.ts`). Así nadie acapara la tele pidiendo diez canciones.
4. Entre canciones, la tele anuncia quién canta con una cuenta atrás de 10 s (Intro la empieza ya).
5. Los móviles hacen de mando (pausa, saltar, voz guía, ton) solo si el anfitrión lo permite.

La cola vive en el servidor; cada pantalla calcula los turnos con la misma función.

## Instalar y cantar sin conexión

La web se instala como app (manifiesto e iconos en `web/static/`) y tiene un service worker propio
(`web/src/service-worker/`): guarda la interfaz para abrirse sin red y, en el panel «Son» del
reproductor, «Gardar sen conexión» descarga la canción entera (letra, audio, portada y vídeo) a
este aparato. Las guardadas salen con una esquina marcada y un filtro «Gardadas» en la biblioteca, y
se gestionan en Axustes. Una versión nueva de la app espera a que se pulse «Actualizar»: nunca
corta una canción.

Necesita HTTPS (o `localhost`): por `http://<ip>` no hay service worker y la opción no aparece.

## Diseño

- **Cartaz**: cada canción es un cartel de verbena o de concierto (portada a dos tintas sobre papel
  de imprenta: kraft, tomate, branco, lila, azul verbena ou noite; título en la condensada tan
  grande como quepa; sin portada, cita el estribillo). El papel y la disposición salen del id de la
  canción, así que un cartel es siempre el mismo, en la biblioteca, al abrir la canción, en el
  fondo del reproductor (las portadas se imprimen igual) y en la tele de la fiesta.
- **«Cantado» es el estado**: el ámbar de la letra (`--farol`) rellena de izquierda a derecha el
  progreso de un karaoke que se está haciendo, la pestaña actual o la barra de posición, que
  dibuja la forma de la canción (dónde se canta).
- **El color es una persona** en la fiesta (naranja, cian, rosa y verde); el ámbar nunca es una
  persona ni un papel de cartel.
- Solo modo oscuro (se usa de noche y en la tele). Tokens en `web/src/lib/ui/styles/tokens.css`.
- Formas: lo que es papel (carteles, filas, tarjetas) es cuadrado; los controles, 10 px; píldoras
  solo para filtros y el nombre de una persona. Las cifras van en la tipografía de cartel (la de
  texto dibuja el cero tachado).
- Tipos: Big Shoulders (carteles y títulos) y Atkinson Hyperlegible Next (texto), autoalojadas y
  recortadas a latino con `scripts/build_web_fonts.py` (licencia OFL junto a cada una).
- Tele: todo dentro del 5 % de margen seguro de cada lado, texto de 28 px o más a 1080p, foco
  blanco de 6 px. Mientras alguien canta, su nombre va arriba en su color y una línea de su color
  avanza abajo con la canción.
- Método: cada cambio visual se revisa con capturas en móvil, portátil y tele
  (`web/dev/shots.mjs`) frente a estas reglas.

## Idiomas

`web/src/lib/i18n/gl.ts` es el diccionario de referencia; `es.ts` y `en.ts` deben tener las mismas
claves (un test lo comprueba). El gallego es el idioma por defecto para cualquier navegador en
gallego, castellano, portugués, catalán, euskera o asturiano; el inglés, para el resto que hable
inglés. Se cambia en Axustes sin recargar, así que una canción no se corta.

## Pruebas

```bash
pnpm --dir web test       # lógica: turnos, editor, cliente, i18n, servidor simulado…
pnpm --dir web test:e2e   # navegador: móvil, portátil y tele, con axe (accesibilidad)
pnpm --dir web build && pnpm --dir web perf   # presupuesto de JavaScript por pantalla
node web/dev/shots.mjs /cantar/demo-sintetico --sizes phone,laptop,tv   # capturas
```

Las pruebas de navegador necesitan el Chromium de Playwright y, en WSL sin root, `LD_LIBRARY_PATH`
apuntando a `libnss3` (ver `docs/subtitulos.md`).

## Límites conocidos

- **HTTPS en casa**: por `http://<ip-del-portátil>` los móviles no tienen modo sin conexión,
  cambio de tono (AudioWorklet), pantalla siempre encendida ni portapapeles. En la tele
  (`localhost`) funciona todo. Lo resuelve el servidor (área C8).
- **iPhone**: solo pone en pantalla completa los `<video>`; instalada en la pantalla de inicio sí
  ocupa toda la pantalla.
- **WSL**: el servidor de desarrollo anuncia la IP interna de WSL en el QR; con
  `networkingMode=mirrored` (ver `docs/audio.md`) los móviles llegan al portátil.
