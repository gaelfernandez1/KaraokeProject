# Calidad del código

Qué comprueba cada puerta, cómo se pasa y cómo auditar el proyecto a fondo. La decisión con el
porqué y lo que se encontró en la auditoría está en
[`plan-v3/decisiones/012-calidad.md`](plan-v3/decisiones/012-calidad.md).

## Las puertas (`make ci` en local, y la CI en GitHub)

| Puerta | Qué evita | Comando |
|---|---|---|
| ruff (formato y lint) | además del estilo: bloquear el bucle del servidor (`ASYNC`), seguridad (`S`), errores tragados (`BLE`), fechas sin zona (`DTZ`), prints fuera de las CLI (`T20`) | `make lint` |
| deptry | que un paquete use algo que no declara (funcionaría por casualidad, porque otro paquete lo trae) | `make lint` |
| import-linter | contratos → motor → banco y servidor, sin imports hacia arriba; y que **el proceso del servidor nunca cargue torch ni los modelos** (solo el proceso de cada trabajo) | `make lint` |
| mypy estricto | tipos en todo el Python | `make typecheck` |
| pytest | 830+ tests; en la CI, con ffmpeg 8 (Ubuntu 26.04) | `make test` |
| Política de saltos | en la CI (`KARAOKE_STRICT_SKIPS=1`) un test solo se puede saltar por no haber GPU, librerías de ML, modelos o canciones descargadas, systemd o medidas solo locales; cualquier otro salto (p. ej. que falte ffmpeg) es un fallo | `conftest.py` |
| Contratos | esquemas JSON, OpenAPI y tipos TS generados al día | `make contracts` |
| Web: prettier, eslint con tipos, knip | además del estilo: promesas sin esperar, `any` que sale de un JSON sin mirar, código y dependencias muertos | `pnpm --dir web lint` |
| Web: svelte-check, vitest, build | tipos (`strict`, `noImplicitOverride`, `noFallthroughCasesInSwitch`) y 340+ tests | `make web` |
| Navegador (Playwright) | la app en móvil, portátil y tele contra el servidor simulado | `pnpm --dir web test:e2e` (también en la CI) |
| Seguridad de los workflows | permisos mínimos, acciones fijadas a un commit, inyecciones | `uvx zizmor@1 --offline .github/workflows` (también en la CI) |

Una regla nueva entra solo con la base limpia. Lo que una regla no puede saber se justifica en la
línea (`# noqa: S310 - fixed https URL`); nunca un `noqa` o un `eslint-disable` sin motivo.

## Tests

- `make test` corre la batería en paralelo (`-n 6`, unos 60 s y 2,5 GB de RAM), sin los tests
  marcados `@pytest.mark.models`, que cargan modelos de verdad (2–3 GB cada fichero): esos van
  aparte con `make test-models`, de uno en uno y cada fichero en su proceso (juntos llegaban a
  4,9 GB), y se niegan a empezar si hay un karaoke haciéndose en la GPU.
- Un test que necesita ffmpeg pide el fixture `ffmpeg` (en `conftest.py`); uno que necesita GPU,
  modelos o canciones se salta con un motivo claro.
- Fuera de la CI, solo en local: `pnpm --dir web test:e2e:server` (la web contra el servidor
  real; necesita el audio de las canciones de ejemplo) y el banco.

## Pruebas por propiedades

- `packages/contracts/tests/test_properties.py` (Hypothesis): el validador responde con problemas,
  nunca con una excepción, a cualquier JSON; guardar y cargar un documento no pierde nada, con
  cualquier texto.
- `packages/server/tests/test_api_schema.py` (Schemathesis): peticiones generadas desde el
  OpenAPI del propio servidor, como dueño y como invitado de casa; ninguna da 5xx.
- La maquetación de la letra existe en Python y en TypeScript: los casos compartidos de
  `fixtures/lyrics-layout/` (`python -m karaoke_engine.subtitles.conformance --write`) los pasan
  las dos; hay casos de líneas largas en vertical.

## Rendimiento

- Motor: el banco mide tiempo y memoria de cada paso (`docs/banco.md`).
- Web: `pnpm --dir web perf` (JavaScript por pantalla, tras `pnpm build`) y
  `pnpm --dir web perf:frames` (tiempo entre fotogramas de la letra con la CPU ralentizada ×4 y
  ×6, como un móvil medio).

## Auditar a fondo (de vez en cuando)

| Qué | Cómo |
|---|---|
| Vulnerabilidades de Python | `uv export --all-extras --no-hashes --no-emit-workspace > /tmp/req.txt && uvx pip-audit -r /tmp/req.txt --no-deps --disable-pip` |
| Vulnerabilidades de la web | `pnpm --dir web audit` |
| Secretos en el historial | gitleaks (`gitleaks git .`), desde una carpeta aparte |
| Código muerto de Python | `uvx vulture packages --min-confidence 80 --exclude '*/tests/*'` (revisar a mano: los modelos de pydantic y las rutas salen como falsos positivos) |
| Una segunda opinión de tipos | `uvx pyrefly check` sobre `packages/*/src` (solo para buscar fallos; no es puerta) |
| Revisión por zonas | contratos y alineación; subtítulos, vídeo y audio; banco; servidor; web del reproductor; web de fiesta, editor y API |
