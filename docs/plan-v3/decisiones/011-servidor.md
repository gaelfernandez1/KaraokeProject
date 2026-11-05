# 011 · Servidor: un proceso, una cola para la GPU y acceso por zonas de red

- **Fecha**: 05/11/2026
- **Estado**: propuesta (área C8); se aprueba con su PR
- **Afecta a**: C7 (la web habla con el servidor real; tipos generados; vincular aparatos), C3/C4/C6
  (el servidor llama a `make_package`, `find_lyrics` y `render` en un proceso aparte), C9 (un
  paquete más: `packages/server`), C10 (arranque, documentación)

## Contexto

El portátil (RTX 3050 de 4 GB, unos 7,6 GB de RAM en WSL) hace los karaokes y los sirve al móvil,
al propio portátil con la tele por HDMI y, si se quiere, a los aparatos del dueño fuera de casa.
Tiene que ser sencillo de arrancar, aguantar que el motor falle sin tumbar nada, no costar dinero y
no dejar que un invitado curioso borre canciones. El sistema viejo (Flask, Celery, Redis, Postgres,
R2, Resend, Sentry, Fly) nunca se desplegó y no tiene karaokes que migrar.

## Qué se miró

- La máquina: WSL 2 con systemd y red NAT (inalcanzable desde la wifi), Windows 11 con Tailscale
  instalado; `/tmp` está en RAM. El 29/10 dos procesos con modelos agotaron la RAM y tumbaron WSL.
- WSL apaga su máquina virtual poco después de que se cierre el último programa de Windows que la
  usa, aunque haya servicios de systemd (microsoft/WSL#13416, reproducido aquí).
- La web de C7 ya espera una API concreta (`decisiones/010`) y la implementa un simulador con tests.

## Enfoques comparados

| Tema | Elegido | Descartado y por qué |
|---|---|---|
| Lenguaje y framework | Python 3.12 + FastAPI (SSE propio, OpenAPI, pydantic como los contratos), uvicorn | Litestar (nada que ganar); servidor en TS a partir del simulador (el motor y la validación de `karaoke.json` son Python: habría que duplicar la validación) |
| Cola para una GPU | propia: tabla SQLite + planificador asyncio + **un proceso hijo por trabajo** | Huey (no cancela un trabajo en marcha ni da progreso); Celery + Redis (dos piezas más); arq/SAQ/procrastinate (Redis o Postgres) |
| Aislar el motor | proceso hijo dentro de un *scope* de systemd con `MemoryMax` | en el mismo proceso (torch no devuelve la RAM, no se puede cancelar y un fallo de CUDA tumba la API); un trabajador permanente con modelos cargados (no caben juntos en 4 GB) |
| Base de datos | `sqlite3` de la biblioteca estándar (WAL, migraciones con `PRAGMA user_version`); los paquetes en disco son la verdad y SQLite, su índice | SQLAlchemy + Alembic (dos dependencias grandes para pocas tablas); Postgres |
| En vivo | SSE, como pidió C7 | WebSocket (más piezas sin necesidad) |
| Acceso | zonas de red + aparatos vinculados con cookie + fichas de invitado de la fiesta | cuentas con contraseña (exceso para una casa); enlaces mágicos por correo (servicio externo y clave); todo abierto (con la fiesta y un túnel, cualquiera borraría); fiarse de las cabeceras de identidad de Tailscale (no existen para aparatos etiquetados y la red Tailscale es compartida) |
| Red de casa | WSL en modo `mirrored` + regla del cortafuegos de Hyper-V solo para el puerto 8765 en perfil privado (pasos del usuario, con administrador) | NAT + `netsh portproxy` (la IP de WSL cambia en cada arranque); servidor en Windows (el motor vive en WSL) |
| Fuera de casa | Tailscale Serve hacia un puerto propio de túneles: HTTPS con certificado real, solo la red Tailscale | Cloudflare Tunnel (dominio propio, expuesto a internet); Tailscale Funnel (público); abrir puertos del router |
| Arranque | acceso directo en la carpeta Inicio de Windows que lanza, sin ventana, un bucle de reinicio en WSL (sin administrador) | servicio de systemd (WSL se apaga igual); Programador de tareas (pide administrador); Docker (la GPU en Docker sobre WSL pide el toolkit de NVIDIA y varios GB, y `uv` ya da un entorno reproducible) |
| Enlaces | yt-dlp siempre en su última versión (`uvx --from 'yt-dlp[default]@latest'`) con Node como motor JavaScript | yt-dlp fijado en el lock (YouTube cambia cada semana) |
| Registros y errores | `logging` estándar: JSON por líneas con rotación + consola; el registro de cada trabajo en su carpeta | Sentry, structlog (servicio externo; nadie mira un panel en una app casera) |
| Canciones con el portátil apagado | no por ahora: las cubren las canciones guardadas sin conexión de la PWA (con HTTPS, por Tailscale) | almacenamiento en la nube (cuenta, canciones con copyright fuera de casa): pregunta abierta al usuario |

## Decisión

- **Paquete `packages/server`** (`karaoke_server`), orden `karaoke-server`. Un proceso uvicorn con
  **dos sockets**: `0.0.0.0:8765` (casa) y `127.0.0.1:8766` (túneles). Sirve la API (`/api`), los
  ficheros de los paquetes (`/media`, con peticiones Range) y la web compilada (`web/build`, con
  `index.html` de respaldo y caché inmutable en `/_app/immutable/`).
- **Zonas**: *local* (desde el propio portátil al 8765: dueño), *casa* (IP privada al 8765: ve,
  canta y monta fiestas), *remota* (todo lo que entra por el 8766, por otra IP, con cabeceras de
  proxy o desde la puerta de enlace de WSL en NAT: solo la app y la página de vincular). **Dueño** =
  zona local o aparato vinculado. Solo el dueño crea, cancela y reintenta trabajos, corrige, borra,
  exporta y gestiona aparatos (`--open-home` lo abre a toda la casa).
- **Vincular**: código de 8 letras sin vocales, 10 minutos, un solo uso; 10 fallos en 10 minutos
  bloquean los intentos; la ficha se guarda con hash y viaja en una cookie `HttpOnly`, `SameSite=Lax`, `Secure`
  por HTTPS, de un año. Los métodos que cambian algo exigen `Origin` propio.
- **Trabajos**: la subida va en streaming al disco (413 antes de leer si pasa de 2 GB), se valida
  con ffprobe (audio, ≤ 20 min) y se lee el título de las etiquetas o del nombre del fichero. Los
  enlaces pasan por un carril de descargas (uno a la vez); la GPU, por otro (uno a la vez), con un
  proceso `python -m karaoke_server.jobs.runner` por trabajo que informa por líneas JSON. Cancelar
  manda `SIGTERM` al grupo y `SIGKILL` a los 5 s. Un reintento automático si el fallo es pasajero
  (sin memoria, el proceso murió); la entrada se guarda 7 días para *Tentar de novo*. Al arrancar,
  lo que estaba en marcha vuelve a la cola. El progreso global y el tiempo restante salen de la
  mediana de lo que tardó cada fase en esta máquina (con valores iniciales medidos).
- **Biblioteca**: `library/<id>/` por canción (con `exports/` para los MP4); corregir valida, marca
  `edited` y guarda una vez `karaoke.original.json`; borrar mueve a `trash/` 30 días.
- **Fiesta**: la del simulador de C7, con el estado en memoria y guardado en SQLite tras cada cambio
  (sobrevive a un reinicio), 24 h de vida y 50 invitados como mucho.
- **Mantenimiento**: `doctor` (cada fallo con su arreglo), `backup` incremental (y diario con
  `KARAOKE_BACKUP_DIR`), `import`, `pair`, `devices`, `prepare`, `openapi`, `autostart`.
- **OpenAPI** en `schemas/openapi.json` y tipos TS generados en `web/src/lib/api/generated/`
  (`make contracts`; la CI comprueba que estén al día).

## API: lo que se añade a la de `decisiones/010`

- `Job`: `error_code` (para traducir el error), `overall` (0–1 del trabajo entero), `eta`
  (segundos), `can_retry`, `attempt`. `POST /api/jobs/{id}/retry`, `GET /api/jobs/{id}/log`.
- Los errores son `{detail, code}` (por ejemplo `not_owner`, `too_big`, `bad_lyrics`).
- `GET /api/me` → `{owner, zone, device}`; `POST /api/devices/pairing` → `{code, expires_at,
  urls}`; `POST /api/devices/pair {code, name?}` (pone la cookie); `GET /api/devices`;
  `DELETE /api/devices/{id}`.
- `GET /api/server` → `{url, home_url, remote_url, home_reachable}` (`url` sigue siendo la del QR
  de la fiesta; `home_reachable` es falso mientras WSL esté en NAT). `GET /api/health`.

## Cambios en ficheros del área C7

Mínimos y con sus tests: `#lib/api/types.ts` y `#lib/party/types.ts` reexportan los tipos
generados; el cliente gana `getMe`, `startPairing`, `pairDevice`, `listDevices`, `revokeDevice`,
`retryJob`; `JobCard` traduce `error_code` y usa `overall`/`eta`; *Tentar de novo* usa el reintento
del servidor; sección «Este aparello» en *Axustes*, ruta `/vincular` y aviso con enlace a *Axustes*
cuando el servidor responde `not_owner`; la tele de la fiesta avisa si los móviles no pueden
entrar; borrar una canción desde «Corrixir a letra» (con confirmación; va a la papelera del
servidor); el reproductor y la calibración avisan si el navegador no saca sonido (en vez de
quedarse en 0:00); `vite.config.ts` hace de proxy al servidor real con `KARAOKE_SERVER`; el simulador
responde `/api/me`, vincular y reintentar; textos en gl, es y en.

## Resultados

En la RTX 3050, a través del servidor (`bench/results/2026-11-05-c8-servidor/`): canción de 4:47
subida con letra en 106 s; de 5:13 por enlace y sin letra en 166 s (141 s sin la descarga); MP4
1080p en 30 s. VRAM pico 2,8 GB y RAM del motor ≤ 3,3 GB. Cancelar en plena separación libera la
GPU en 0,3 s sin dejar procesos. 241 tests del servidor y pruebas de navegador contra el servidor
real (biblioteca, subir hasta cantar, vincular un móvil, fiesta con tele y móviles, editor).

## Consecuencias

- Hasta que el usuario active el modo `mirrored` y la regla del cortafuegos, los móviles no llegan
  al portátil por la wifi (la tele y `doctor` lo dicen).
- Los móviles por `http://` en casa no tienen modo sin conexión, cambio de tono ni pantalla
  encendida; por Tailscale (HTTPS) sí. Un certificado válido para la IP de casa pediría una cuenta
  (DNS dinámico): pregunta abierta.
- El servidor arranca al iniciar sesión en Windows, no antes, y se para si Windows suspende el
  portátil (se documenta el ajuste de energía en `docs/servidor.md`).
- C9: `packages/server` entra en ruff, mypy estricto y pytest; las pruebas de navegador contra el
  servidor real son `pnpm --dir web test:e2e:server` (no van en la CI: necesitan el entorno
  completo).
