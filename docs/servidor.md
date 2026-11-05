# Servidor

El portátil hace los karaokes con su tarjeta gráfica y los sirve a todos los aparatos: el propio
portátil (y la tele conectada por HDMI), los móviles de casa y, si quieres, tus aparatos fuera de
casa. Todo lo hace un programa, `karaoke-server`, que corre dentro de WSL. Las decisiones de diseño
están en [`plan-v3/decisiones/011-servidor.md`](plan-v3/decisiones/011-servidor.md).

## Lo esencial

- **Una orden para arrancarlo**: `make serve`. Después, en el portátil, abre
  <http://localhost:8765>.
- **Quién puede hacer qué**:
  - El **portátil** puede hacerlo todo.
  - Un **móvil en la wifi de casa** puede ver las canciones, cantarlas y montar o unirse a una
    fiesta. Para crear, corregir o borrar canciones hay que **vincularlo** una vez.
  - **Fuera de casa** (por Tailscale) solo entran los aparatos vinculados.
  - Los **invitados** de una fiesta entran con el QR de la tele y solo piden canciones y hacen de
    mando.
- **Vincular un aparato**: en el portátil, *Axustes → Este aparello → Vincular outro aparello*.
  Sale un código de 8 letras (vale 10 minutos y una sola vez) y un QR. En el otro aparato, escanea
  el QR o escribe el código en *Axustes*. También vale `uv run karaoke-server pair` en la terminal.
- **Dónde está todo**: `~/.local/share/karaoke/` (dentro de WSL):
  - `library/`: una carpeta por canción, con los MP4 exportados en `exports/`.
  - `karaoke.db`: la base de datos (trabajos, aparatos, fiestas).
  - `jobs/`: lo que se está procesando.
  - `trash/`: canciones borradas; se vacía sola a los 30 días.
  - `logs/`: los registros.

  Se puede cambiar con `--data` o con la variable `KARAOKE_DATA`.

## La primera vez

Con el entorno ya instalado (`docs/desarrollo.md`), desde la carpeta del proyecto en WSL:

```bash
uv sync --extra ml --inexact          # el motor con la GPU (si no está ya)
pnpm --dir web build                  # la aplicación web
uv run karaoke-server prepare --lang gl   # descarga los modelos (unos GB, una vez)
uv run karaoke-server doctor          # qué falta y cómo arreglarlo
make serve
```

`doctor` revisa ffmpeg, la GPU, NVENC, los modelos, yt-dlp, el límite de memoria de los
trabajos, el espacio libre, la web compilada, la red de casa, Tailscale y el arranque automático.
Cada fallo viene con su solución.

Si ya tienes paquetes hechos con `karaoke make`, se meten en la biblioteca con:

```bash
uv run karaoke-server import ruta/al/paquete [otro/paquete …]
```

## Que los móviles de casa lleguen al portátil

WSL, por defecto, vive en una red interna (NAT) a la que los móviles no llegan. Mientras siga así,
la tele de la fiesta lo avisa debajo del código y `doctor` también. Hay que hacer dos cambios en
Windows, **una sola vez**:

### 1. Poner WSL en modo «espejo»

1. En Windows, pulsa `Win + R`, escribe `%UserProfile%` y pulsa Enter. Se abre tu carpeta de
   usuario.
2. Busca un fichero llamado `.wslconfig`. Si no existe, créalo: clic derecho → *Nuevo →
   Documento de texto*, y llámalo `.wslconfig` (sin `.txt` al final; si Windows esconde las
   extensiones, actívalas en *Ver → Mostrar → Extensiones de nombre de archivo*).
3. Ábrelo con el Bloc de notas y pon esto (si ya tiene una sección `[wsl2]`, añade solo la línea
   de `networkingMode` debajo de ella):

   ```ini
   [wsl2]
   networkingMode=mirrored
   ```

4. Guarda y cierra.
5. Abre **PowerShell** (menú Inicio → escribe «PowerShell») y ejecuta `wsl --shutdown`. Espera unos
   10 segundos y vuelve a abrir la terminal de Ubuntu.

### 2. Abrir el puerto 8765 en el cortafuegos, solo en redes privadas

1. Menú Inicio → escribe «PowerShell» → clic derecho → **Ejecutar como administrador**.
2. Copia y pega esta orden (es una sola línea):

   ```powershell
   New-NetFirewallHyperVRule -Name Karaoke -DisplayName "Karaoke (WSL)" -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -Protocol TCP -LocalPorts 8765 -Profiles Private
   ```

3. Comprueba que tu wifi de casa está marcada como **privada**: *Configuración → Red e Internet →
   Wi-Fi →* (tu red) *→ Tipo de perfil de red → Red privada*. En una red pública (un bar, un tren)
   el puerto sigue cerrado, que es lo que queremos.

Solo se abre el puerto del karaoke, no toda la máquina virtual.

### 3. Comprobarlo

1. Arranca el servidor (`make serve`) y ejecuta `uv run karaoke-server doctor`: la línea
   «home network» debe salir con ✓ y una dirección como `http://192.168.1.38:8765`.
2. En el móvil, conectado a la misma wifi, abre esa dirección. Debe salir la biblioteca.
3. Si no carga: revisa que la wifi sea privada (paso 2.3) y que el móvil no esté en una red de
   invitados del router (aislan los aparatos entre sí).

## Fuera de casa: Tailscale

Tailscale crea una red privada entre tus aparatos y da al portátil una dirección `https://` con
certificado de verdad. Ya está instalado en Windows. Con HTTPS, además, el móvil gana lo que el
navegador solo permite en conexiones seguras: guardar canciones sin conexión, cambiar el tono y
mantener la pantalla encendida (por eso merece la pena usarlo también en casa).

1. En PowerShell (de Windows, no hace falta administrador):

   ```powershell
   tailscale serve --bg 8766
   ```

   El puerto 8766 es la puerta del servidor para túneles: todo lo que entra por ahí se trata como
   «de fuera», también si alguien de tu red Tailscale lo abre. Si Tailscale te pide activar HTTPS
   en tu red, sigue el enlace que imprime. **No lo apuntes al 8765**: `doctor` avisa si pasa.
2. `uv run karaoke-server doctor` enseña la dirección (`https://<portátil>.<tu-red>.ts.net`).
3. En el móvil, instala la app de Tailscale con la misma cuenta, abre esa dirección y vincula el
   móvil (en casa, con el QR de *Axustes*; o escribiendo el código).

Para quitarlo: `tailscale serve --https=443 off`.

Los invitados de una fiesta no necesitan Tailscale: entran por la wifi de casa.

## Que arranque solo al encender

```bash
uv run karaoke-server autostart install    # crea un acceso directo en la carpeta Inicio de Windows
uv run karaoke-server autostart status
uv run karaoke-server autostart remove
```

Al iniciar sesión en Windows se lanza, sin ventana, `scripts/serve-forever.sh`, que arranca el
servidor y lo vuelve a arrancar a los 5 s si se cae. Mientras corre, WSL se mantiene encendido.
Sus mensajes van a `~/.local/share/karaoke/logs/forever.log`.

- **Ajustes** para el arranque automático (como la carpeta de copias): en
  `~/.config/karaoke/server.env`, una línea por ajuste, por ejemplo
  `KARAOKE_BACKUP_DIR=/mnt/d/CopiasKaraoke`.
- **Pararlo**: `pkill -f "[k]araoke-server serve"` (sale limpio y el bucle no lo relanza). Para
  volver a arrancarlo sin cerrar sesión: `make serve`, o doble clic en el acceso directo «Karaoke
  server» de la carpeta Inicio (`Win + R` → `shell:startup`).
- Arranca **al iniciar sesión**, no antes. Para que arranque con la sesión cerrada haría falta el
  Programador de tareas con permisos de administrador.

### Energía y tapa

Si Windows suspende el portátil, el servidor deja de responder. Para las fiestas y para crear
karaokes desde el móvil:

- *Configuración → Sistema → Energía → Pantalla, suspensión e hibernación*: con el cargador
  conectado, «Poner el dispositivo en suspensión» → **Nunca**.
- *Panel de control → Opciones de energía → Elegir el comportamiento del cierre de la tapa*: con
  corriente, **No hacer nada** (así puedes cerrarlo con la tele conectada).

## Copias de seguridad

```bash
uv run karaoke-server backup --to /mnt/d/CopiasKaraoke
```

Copia la base de datos (en caliente, sin parar nada) y las canciones; la segunda vez solo copia
lo que cambió. Los MP4 exportados no se copian (se pueden volver a hacer). Una canción que ya no
está en la biblioteca no se borra de la copia: se aparta a `_borrado/<fecha>/`. `/mnt/d/…` es el
disco D: de Windows; una carpeta de OneDrive o Google Drive también vale.

Con `KARAOKE_BACKUP_DIR` (en `~/.config/karaoke/server.env` o en el entorno), el servidor hace la
copia solo, una vez al día.

**Recuperar**: con el servidor parado, copia `karaoke.db` y `library/` de la copia a
`~/.local/share/karaoke/`.

## Crear karaokes

Desde *Crear* (portátil o aparato vinculado): un fichero de audio o vídeo, o un enlace. Límites:
2 GB, 20 minutos y que queden 2 GB libres en el disco.

- Los **enlaces** se descargan con yt-dlp, siempre en su última versión (la baja `uvx` la primera
  vez; YouTube cambia a menudo y una versión vieja deja de funcionar). Es «lo mejor que se puede»:
  algunos sitios fallan. No se aceptan directos ni listas.
- Los trabajos van **de uno en uno** por la tarjeta gráfica, cada uno en su propio proceso con un
  límite de memoria: si uno se queda sin memoria, muere él y no WSL. Las descargas avanzan a la vez.
- Un fallo pasajero (sin memoria, el proceso cayó) se reintenta solo una vez. *Tentar de novo*
  reintenta sin volver a subir el fichero (la entrada se guarda 7 días).
- Si el servidor se para con un trabajo a medias, al volver lo retoma.

Tiempos en la RTX 3050 (`bench/results/2026-11-05-c8-servidor/`): canción de 4 min con letra,
unos 90 s; sin letra, unos 110 s; exportar el MP4, unos 25 s.

## Si algo falla

| Qué pasa | Qué hacer |
|---|---|
| El móvil no abre la dirección de casa | `doctor`; revisa el modo espejo, la regla del cortafuegos y que la wifi sea privada |
| La tele de la fiesta dice que los móviles no pueden entrar | lo mismo: WSL sigue en NAT |
| «Isto só se pode facer dende o portátil ou un aparello vinculado» | vincula ese aparato (*Axustes*) |
| Un enlace falla al descargar | prueba más tarde (yt-dlp se actualiza solo) o baja el fichero y súbelo |
| Un trabajo falla | *Tentar de novo*; el registro del trabajo está en `GET /api/jobs/<id>/log` y en `~/.local/share/karaoke/jobs/<id>/log.txt` |
| El servidor no arranca | `~/.local/share/karaoke/logs/server.log` y `forever.log`; ¿otro programa usa el 8765? (`ss -ltnp \| grep 8765`) |
| Desvincular un aparato perdido | *Axustes → Aparellos vinculados*, o `uv run karaoke-server devices --revoke <id>` |

## Para desarrollar

- `pnpm --dir web dev` usa el servidor simulado (`web/dev/mock/`). Con
  `KARAOKE_SERVER=http://127.0.0.1:8765 pnpm --dir web dev`, la web en desarrollo habla con el
  servidor de verdad.
- `uv run karaoke-server serve --fake-engine` hace karaokes de mentira (el paquete sintético) sin
  GPU, en un segundo.
- `pnpm --dir web test:e2e:server`: pruebas de navegador contra el servidor de verdad con el motor
  falso y una biblioteca nueva (el portátil por `localhost`, los móviles por la IP de la máquina).
- La API se describe en `schemas/openapi.json` (`make contracts` la regenera junto con los tipos
  de la web en `web/src/lib/api/generated/`).
- Puertos: 8765 (casa, `KARAOKE_PORT`) y el siguiente, 8766 (túneles, solo en `127.0.0.1`).
