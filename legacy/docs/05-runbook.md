# 05 — Runbook de operaciones (F13)

> Guía operativa de la **beta privada** en producción. Despliegue, rollback, migraciones,
> debug de BD, topología del worker, coste de Modal y rotación de secrets.
>
> **Estado**: beta privada con registro cerrado por allowlist (`ALLOWED_EMAILS`).
> Monetización (F11 cuotas, F12 billing) diferida.

---

## 1. Arquitectura en producción

```
Usuario ──HTTPS──> Fly.io (web, Flask+gunicorn, shared-cpu-1x, scale-to-zero)
                      │  encola job en ───────────────> Upstash Redis (broker Celery)
                      │  lee/escribe ─────────────────> Neon Postgres
                      │  sirve URLs firmadas de ───────> Cloudflare R2
                      │  errores ─────────────────────> Sentry
                      ▼
            Worker (procesa el job): hoy LOCAL en tu máquina con GPU,
            apuntando a Upstash/Neon/R2 de producción. Opcional: Modal (GPU serverless).
```

- **El web de Fly NO renderiza** (sin GPU): solo encola jobs y sirve resultados desde R2.
- **El worker** consume del broker Upstash. En la beta corre **en tu máquina** (ver §7).
  Alternativa serverless: Modal (ver §8), desactivada por defecto (`MODAL_DISPATCH=false`).

---

## 2. Secrets de producción (Fly)

Nunca se commitean. Se cargan con `flyctl secrets set` (cada `set` dispara un rolling restart).
`STORAGE_BACKEND=r2` y `APP_BASE_URL` ya viven en `fly.toml [env]` (no son secretos).

```bash
flyctl secrets set \
  FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  DATABASE_URL="postgresql+psycopg://USER:PASS@HOST/neondb?sslmode=require" \
  REDIS_URL="rediss://default:PASS@HOST:PORT" \
  RESEND_API_KEY="re_..." \
  SENTRY_DSN="https://...@oXXXX.ingest.sentry.io/XXXX" \
  R2_ACCOUNT_ID="..." \
  R2_BUCKET="karaoke-outputs" \
  R2_ACCESS_KEY_ID="..." \
  R2_SECRET_ACCESS_KEY="..." \
  ALLOWED_EMAILS="tu@correo.com,colaborador@correo.com"
```

Notas:
- **Neon**: la URL lleva `?sslmode=require`. Usa el driver `+psycopg` (psycopg3, ya en core).
  Verificado: psycopg3 acepta `?sslmode=require` sin cambios.
- **Upstash + Celery sobre TLS**: si el broker no conecta con `rediss://`, añade explícitamente
  `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND` con la URL Upstash y `?ssl_cert_reqs=required`.
  Por defecto el broker/backend caen a `REDIS_URL`, así que normalmente basta con `REDIS_URL`.
- Paddle (`PADDLE_API_KEY`, `PADDLE_WEBHOOK_SECRET`) se añaden en F12, no ahora.

Listar nombres de secrets cargados (sin valores): `flyctl secrets list`.

---

## 3. Setup inicial (una vez)

```bash
# 0. Autenticarse
flyctl auth login

# 1. Crear la app (o `fly launch --no-deploy` reutilizando el fly.toml del repo;
#    si pregunta por sobrescribir fly.toml, di que NO).
flyctl apps create karaoke-web        # usa el mismo nombre que `app` en fly.toml

# 2. Cargar los secrets (§2).

# 3. Primer deploy. El release_command corre `alembic upgrade head` en una máquina
#    temporal ANTES de arrancar la app, así Neon queda migrado y stamped.
flyctl deploy --remote-only

# 4. Comprobar salud
curl -i https://karaoke-web.fly.dev/health     # 200 {"status":"ok",...}
```

---

## 4. Deploy

**Automático**: cada push a `main` lanza el workflow `CI`; si pasa, el workflow `Deploy`
(`deploy-web`) despliega el commit exacto que pasó CI vía `flyctl deploy --remote-only`.
Requiere el GitHub Secret `FLY_API_TOKEN` (genéralo con `flyctl tokens create deploy`).

**Manual** (hotfix sin push, o redeploy):

```bash
flyctl deploy --remote-only
```

---

## 5. Rollback

```bash
# Ver releases (versión, estado, imagen)
flyctl releases list

# Opción A: rollback a la versión anterior
flyctl releases rollback              # o: flyctl releases rollback <version>

# Opción B: redeploy de una imagen concreta (de `flyctl releases list` / `flyctl image show`)
flyctl deploy --image registry.fly.io/karaoke-web@sha256:<digest>
```

> Cuidado con las migraciones: un rollback de imagen **no revierte el esquema**. Si el release
> roto aplicó una migración incompatible, haz primero `alembic downgrade -1` (§6) y luego el
> rollback de imagen.

---

## 6. Migraciones en producción

Lo normal es automático: el `release_command` de `fly.toml` corre `alembic upgrade head` en
cada deploy. Para ejecutarlas a mano:

```bash
# Aplicar todas las pendientes
flyctl ssh console --command "alembic upgrade head"

# Revertir la última (p.ej. antes de un rollback)
flyctl ssh console --command "alembic downgrade -1"

# Ver la revisión actual
flyctl ssh console --command "alembic current"
```

`alembic.ini` tiene `sqlalchemy.url` vacío a propósito: `env.py` lee `DATABASE_URL` vía
`Settings`, así que dentro de la máquina de Fly apunta a Neon automáticamente.

---

## 7. Worker en la beta (local contra producción)

El web de Fly publica jobs en Upstash. Para procesarlos, corre el worker **en tu máquina con
GPU** apuntando a la infra de producción. El más simple: reutilizar los contenedores
`celery_worker` + `whisperx` de docker-compose, pero con env de prod.

Crea un `.env.prod-worker` (no se commitea) con:

```bash
FLASK_SECRET_KEY=<el mismo que en Fly>
DATABASE_URL=postgresql+psycopg://USER:PASS@HOST/neondb?sslmode=require   # Neon
CELERY_BROKER_URL=rediss://default:PASS@HOST:PORT                          # Upstash
CELERY_RESULT_BACKEND=rediss://default:PASS@HOST:PORT                      # Upstash
STORAGE_BACKEND=r2
R2_ACCOUNT_ID=...
R2_BUCKET=karaoke-outputs
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
MODAL_DISPATCH=false
```

Arranca solo el worker y whisperx con ese env (redis local no hace falta, el broker es Upstash):

```bash
docker compose --env-file .env.prod-worker up -d celery_worker whisperx
docker compose logs -f celery_worker
```

El worker consume de Upstash, renderiza con tu GPU, sube a R2 y guarda en Neon. El web sirve
la URL firmada de R2. Cuando termines la sesión de beta, `docker compose stop celery_worker whisperx`.

> Esto evita pagar GPU mientras la beta es de bajo volumen. Cuando quieras GPU 24/7 sin tu
> máquina encendida, pasa a Modal (§8).

---

## 8. Modal (GPU serverless, opcional)

Desactivado por defecto. Antes de activarlo: la imagen de `modal/karaoke_worker.py` replica el
setup delicado de ffmpeg/av/ImageMagick de `Dockerfile.worker` y probablemente pida una o dos
iteraciones de `modal deploy`; además los inputs de tipo *upload* necesitan staging en R2 y
WhisperX tiene que ser alcanzable desde Modal (`WHISPERX_SERVICE_URL`).

```bash
# 1. Crear el secret que la función Modal lee como env (Settings())
modal secret create karaoke-secrets \
  FLASK_SECRET_KEY=... \
  DATABASE_URL='postgresql+psycopg://USER:PASS@HOST/neondb?sslmode=require' \
  STORAGE_BACKEND=r2 \
  R2_ACCOUNT_ID=... R2_BUCKET=karaoke-outputs \
  R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=... \
  WHISPERX_SERVICE_URL=https://<whisperx-alcanzable>

# 2. Desplegar la función (o usar el job manual `deploy-modal` en GitHub Actions)
modal deploy modal/karaoke_worker.py

# 3. Activar el dispatch en el web (rolling restart). NO hacerlo sin querer.
flyctl secrets set MODAL_DISPATCH=true
```

Con esto, la tarea Celery hace `modal.Function.from_name("karaoke-gpu", "run_karaoke_job").remote(...)`
en vez de procesar localmente.

### Coste estimado por karaoke en Modal T4

Precios Modal (consultados en https://modal.com/pricing):

| Recurso | Precio |
|---|---|
| GPU Nvidia T4 | $0.000164 / s (≈ $0.59/h) |
| CPU | $0.0000131 / core / s |
| Memoria | $0.00000222 / GiB / s |

Para una canción ~4 min, asumiendo ~6 min (360 s) de wall-clock en la máquina T4 (Demucs en
GPU + espera HTTP a WhisperX + render MoviePy en CPU, con la GPU facturándose todo el rato):

```
GPU:  360 s × $0.000164         = $0.0590
CPU:  360 s × 1 core × $0.0000131 = $0.0047
Mem:  360 s × 4 GiB × $0.00000222 = $0.0032
                                  ─────────
Total por karaoke               ≈ $0.067   (~7 céntimos)
```

Rango realista: **$0.05 (4 min) – $0.09 (8 min)**, dominado por la GPU. No incluye:
- **Cold start** (descarga de imagen + modelos): añade segundos → unos céntimos en la 1ª llamada
  tras un periodo idle. Mitigación: imagen con modelos embebidos.
- Un servicio **WhisperX en GPU aparte**, si lo corres en Modal (sería coste adicional propio).
- Créditos gratuitos de Modal, que absorben el uso inicial.

A ~$0.07/karaoke, un free tier de 5 karaokes/mes cuesta ~$0.35/usuario (referencia para F11).

---

## 9. Conectarse a la BD de producción (debug)

```bash
# Opción A: shell dentro de la máquina de Fly y python con la app
flyctl ssh console
#   > python -c "from karaoke.infra.db import session_scope; from karaoke.infra.db.repository import *; ..."

# Opción B: psql directo contra Neon (necesitas la DATABASE_URL de Neon a mano)
psql "postgresql://USER:PASS@HOST/neondb?sslmode=require"

# Opción C: túnel local a Neon y conectar con tu cliente preferido
#   (Neon es accesible por internet; normalmente basta la Opción B)
```

> Solo lectura para diagnóstico salvo que sepas exactamente qué tocas. Cualquier cambio de
> esquema va por una migración Alembic, no por SQL manual.

---

## 10. Rotar secrets en Fly sin downtime

`flyctl secrets set` aplica los cambios con un **rolling restart** (las máquinas se reinician de
una en una; con scale-to-zero y una sola máquina hay un parpadeo mínimo). Para varios secrets a
la vez, pásalos en un único comando (un solo restart). Para preparar el cambio sin reiniciar aún:

```bash
# Cargar sin reiniciar todavía...
flyctl secrets set CLAVE=nuevo_valor --stage
# ...y aplicarlo en el próximo deploy
flyctl deploy --remote-only
```

Procedimiento de rotación típico (p.ej. `FLASK_SECRET_KEY`, R2 keys, `RESEND_API_KEY`):
1. Generar el nuevo valor en el proveedor (Cloudflare/Resend/Sentry).
2. `flyctl secrets set CLAVE=nuevo` (rolling restart automático).
3. Verificar `/health` y un login.
4. Revocar el valor viejo en el proveedor.

> Rotar `FLASK_SECRET_KEY` invalida las sesiones y los magic links en vuelo (los usuarios
> vuelven a loguearse). Hazlo en ventana de bajo tráfico.

---

## Apéndice — GitHub Secrets (para los workflows)

| Secret | Para | Cómo obtenerlo |
|---|---|---|
| `FLY_API_TOKEN` | `deploy-web` | `flyctl tokens create deploy` |
| `MODAL_TOKEN_ID` | `deploy-modal` | `modal token new` (dashboard Modal) |
| `MODAL_TOKEN_SECRET` | `deploy-modal` | idem |
