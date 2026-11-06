# 013 · Proyecto profesional: una versión, releases desde el CHANGELOG y licencias vigiladas

- **Fecha**: 06/11/2026
- **Estado**: aceptada (área C10, PR #12; v3.0.0 publicada el 06/11/2026)
- **Afecta a**: todas las áreas (versión única, `make lint`, `make install`, `--version`); C3
  (`diffq` fuera), C4 (paquete de demostración), C7 (nombre definitivo), C8 (`--version`,
  `serve-forever.sh`)

## Contexto

Con C1–C9 en `main`, el código era sólido pero el repo no lo contaba: el README describía el
sistema viejo (Docker, Celery), las versiones iban de 0.0.0 a 1.0.0 según el fichero, no había
releases, CHANGELOG, política de seguridad, plantillas ni reglas en `main`, y `CITATION.cff` no era
válido. El objetivo del área se ajustó: un repo **profesional en general**, no centrado en la
comunidad de software libre, aunque siga siendo público y MIT.

## Qué se miró

- Dependabot (ecosistemas `uv`, `npm` con pnpm 7–12 y `github-actions`; *cooldown* por defecto
  desde julio de 2026) frente a Renovate (mejor con monorepos, pero exige instalar una app).
- *Rulesets* de GitHub para un único mantenedor; releases inmutables (GA desde octubre de 2025).
- release-please y git-cliff (necesitan *conventional commits*; aquí los commits van en tono
  humano); Keep a Changelog 1.1.0.
- Contributor Covenant 3.0; esquemas de check-jsonschema para workflows, Dependabot, formularios
  de issues y CITATION.cff.
- Licencias de cada modelo por defecto y de cada paquete instalado, con y sin la parte de GPU.

## Enfoques comparados

| Tema | Opciones | Elegido |
|---|---|---|
| Idioma de la portada | gallego · inglés con gl y es · tres iguales | **gallego (`README.md`) + `README.en.md` y `README.es.md`** (lo eligió el dueño): la identidad es gallega; las otras dos llegan a cualquiera |
| Versiones | una por paquete · una del producto | **una (3.0.0)** en los paquetes, la web y `CITATION.cff`, comprobada en `make lint` |
| Releases | release-please · git-cliff · a mano | **CHANGELOG a mano** y un workflow que, con la etiqueta, comprueba versiones y deja la release en borrador con sus notas |
| Dependencias | Dependabot · Renovate | **Dependabot**: nativo; mensual y agrupado |
| Instalación | `curl \| sh` · Docker · script del repo | **`make install`**: idempotente, sin sudo, probado en la CI dos veces en un Ubuntu limpio |
| Licencias | lista a mano · comprobador | **los dos**: `NOTICE.md` con lo que importa y `scripts/licenses.py` en `make lint` |
| Demo | GIF · vídeo · demo en vivo | **GIF del reproductor real, capturas y un MP4** con una canción gallega CC BY-SA |
| Documentación | web aparte · markdown | **markdown** (GitHub lo pinta bien; una web sería otra pieza); **las guías técnicas en inglés** (lo pidió el dueño), con nombres en inglés; el plan y las decisiones, en castellano |

## Decisión

- **Nombre**: **Proxecto Karaoke en Galego** (lo eligió el dueño; «Foliada», el provisional de
  C7, desaparece de todo lo visible). La portada dice que está hecho para el gallego y funciona en
  cualquier idioma. Icono: la «K» medio cantada, con la letra de Big Shoulders; portada y vista
  previa social con el nombre en dos líneas, como una pantalla de karaoke (`web/dev/brand.mjs`).
  Las claves internas del navegador (`foliada.*`) se quedan, para no perder ajustes ni canciones
  guardadas.
- **Versión 3.0.0** en todo el producto; `scripts/release.py` la comprueba, la cambia y saca las
  notas de cada versión del CHANGELOG; `--version` en `karaoke`, `karaoke-server` y
  `karaoke-bench`. Guía: [`docs/releasing.md`](../../releasing.md).
- **Ficheros del proyecto**: README en gallego, inglés y castellano, `CHANGELOG.md`, `NOTICE.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md` (Contributor Covenant 3.0), `CONTRIBUTING.md`, formularios de issues,
  plantilla de PR, `.editorconfig`, `.gitattributes` y `CITATION.cff` válido (el software como
  cita; el TFG como referencia).
- **Puertas nuevas** en `make lint`: versiones, licencias, shellcheck, esquemas de los ficheros de
  GitHub y de `CITATION.cff`; en los tests, ningún enlace relativo de un `.md` apunta a algo que no
  esté en el repo (`scripts/check_links.py`). En la CI, un job que instala en limpio.
- **`diffq` fuera**: audio-separator lo pide solo para sus modelos Demucs y su licencia es no
  comercial (CC BY-NC 4.0); el motor no lo carga nunca (la separación real pasa sin él).
- **Demo**: «laverca» de Clo Plas (CC BY-SA 4.0) como paquete de ejemplo
  (`fixtures/packages/cloplas-laverca`), hecho por el motor sin tocarlo a mano; capturas y GIF con
  `web/dev/readme-media.mjs`.
- **GitHub** (con el OK del dueño): descripción y temas, *ruleset* de `main` (PR y comprobaciones
  obligatorias, sin force-push), avisos privados de vulnerabilidades, escaneo de secretos,
  actualizaciones de seguridad, CodeQL y releases inmutables.

## Consecuencias

- Subir de versión es `release.py set`, `uv lock` y `make contracts`; la CI falla si algo queda
  atrás.
- Una dependencia con licencia no aceptada rompe `make lint` hasta cambiarla o revisarla.
- Por debajo de lo mejor: no hay demo en vivo en la web (la app usa rutas absolutas y el audio
  separado no se puede hacer en la CI); Dependabot
  con workspaces de uv tiene fallos conocidos (si sus PR no refrescan el lock, la CI lo dirá y se
  valora Renovate).
- Hallado al hacer la demo (para C4): en «laverca» la primera palabra («A», confianza 0,64) quedó
  en 3,98 s cuando se canta en 31,9 s, y la última de esa línea 2 s tarde. Son 2 de 378 palabras
  (el banco sigue en 99,8 %), pero se ven en la primera línea y en el editor.
