# 012 · Calidad: fallos encontrados por zonas y puertas que no los dejan volver

- **Fecha**: 06/11/2026
- **Estado**: propuesta (área C9); se aprueba con su PR
- **Afecta a**: todas las áreas (reglas nuevas en `make ci` y en la CI); C4 (letras y pronombres),
  C5 (maquetación), C6 (vídeo), C7 (fiesta, reproductor, editor), C8 (servidor; un endpoint
  nuevo), C2 (cómo puntúa el banco), C3 (audio del paquete)

## Contexto

Con C1–C8 en `main`, el código tenía 790 tests y un 95 % de cobertura, pero la CI se saltaba 155
(20 %) por no tener ffmpeg, los tests llegaban a 4,9 GB de RAM en un proceso, `legacy/` traía 83
de las 85 alertas de Dependabot y había reglas que nadie comprobaba (dependencias declaradas,
fronteras entre paquetes). La cobertura no dice si el código hace lo que debe.

## Qué se miró

- Herramientas de 2026: mypy 2 (estricto, ya limpio), Pyrefly 1.x y ty 0.0.x; Hypothesis,
  Schemathesis 4, fast-check; mutmut y cosmic-ray; import-linter; deptry, pip-audit, knip;
  zizmor y gitleaks; imágenes `ubuntu-26.04` de GitHub (vista previa, ffmpeg 8 como el portátil).
- Siete revisiones independientes de solo lectura: contratos y alineación; subtítulos, vídeo y
  audio; banco; servidor; web del reproductor; web de fiesta, editor y API; seguridad.

## Enfoques comparados

| Enfoque | Veredicto |
|---|---|
| Todo al máximo de golpe (ruff `ALL`, dos comprobadores de tipos, TS al máximo, mutación en la CI) | no: miles de avisos de estilo, dos juegos de reglas y horas de CI para pocos fallos reales |
| Leer y arreglar lo que se vea | insuficiente: no impide que vuelva |
| Solo añadir herramientas | no: CI roja o llena de excepciones |
| **Detectores por clase de fallo, arreglo con test que falla primero y una puerta solo donde caza fallos reales** | **elegido** |

## Decisión

- **Fuera `legacy/`** (sigue en la etiqueta `v2-final`) y sus exclusiones.
- **Puertas nuevas**: ruff con `ASYNC, S, BLE, DTZ, PIE, PGH, PLE, PLW, T20, C4, LOG, G` y parte de
  `TRY` (se probaron `ARG`, `FAST` y `PERF`: solo marcaban dependencias de FastAPI, firmas de
  protocolo y microoptimizaciones); deptry; import-linter (el proceso del servidor no importa
  torch ni los modelos); eslint con tipos en `src/` (promesas, `any`); knip; zizmor; TS con
  `noImplicitOverride` y `noFallthroughCasesInSwitch`.
- **CI sin puntos ciegos**: Python en `ubuntu-26.04` con ffmpeg y `KARAOKE_STRICT_SKIPS=1` (un
  salto no permitido es un fallo); pruebas de navegador con el simulador; permisos de solo
  lectura y acciones fijadas a un commit.
- **Tests sanos**: marca `models` (cada fichero con modelos en su proceso, pico de 4,9 a 2,8 GB) y
  la batería en paralelo (de 167–188 s a unos 60 s).
- **Propiedades** (Hypothesis en contratos, Schemathesis contra la API) y casos compartidos de
  maquetación con líneas largas.
- **API**: `DELETE /api/parties/{code}` (solo la tele) y el evento `ended` en el SSE de la fiesta;
  todos los errores con `{detail, code}` (también validación, rutas y formularios rotos); `HEAD`
  en `/media` y en la app; cabeceras contra marcos (`X-Frame-Options`,
  `frame-ancestors 'none'`).

## Lo encontrado y arreglado (cada uno con un test que fallaba antes)

| Zona | Fallo | Arreglo |
|---|---|---|
| Seguridad | `karaoke-server import` copiaba los enlaces simbólicos de un paquete ajeno y servía esos ficheros a la wifi de casa | se copian solo `karaoke.json`, los medios que nombra y la licencia, nunca enlaces |
| Seguridad | un aparato probando códigos bloqueaba la vinculación para todos, dueño incluido; tokens y códigos en el log de accesos; la app se podía enmarcar | bloqueo por cliente; log sin tokens; cabeceras contra marcos |
| Fiesta (tele) | tras una canción terminada, la siguiente se daba por cantada sin cantarla (el reproductor no olvidaba el final) | el reproductor empieza limpio cada canción; la tele espera a que la canción esté cargada |
| Fiesta (tele) | si el sonido fallaba a mitad, la fiesta se quedaba congelada | la canción se salta a los 8 s |
| Fiesta (móviles) | terminar la fiesta no llegaba a los móviles | endpoint de fin y evento `ended`; el móvil lo dice |
| Reproductor | tras hacer clic en la imagen, el teclado dejaba de funcionar | el botón de la imagen nunca toma el foco |
| Reproductor | en iPhone con el interruptor de silencio no sonaba nada; una llamada dejaba la letra congelada en «reproduciendo» | sesión de audio de «reproducción»; pausa cuando el sistema quita el sonido |
| Tele | con el mando no se llegaba al buscador, los filtros ni el menú | las flechas recorren toda la página |
| Sin conexión | con el servidor caído tras Tailscale (502) no se veían las canciones guardadas | un 5xx cuenta como sin red |
| Editor | lo que se corregía mientras se guardaba se perdía sin aviso | se conserva y queda por guardar |
| Letra (maquetación) | las líneas largas de rap se cortaban por los lados en el móvil vertical y en el MP4 9:16 | hasta 4 filas equilibradas y, solo si no basta, letra más pequeña: nunca se corta |
| Letra (MP4) | con el tema `moderno` nunca salía el título | sus primeras líneas aparecen `lead_in` antes de cantarse |
| Letras pegadas | «[Estribillo] x2», «2x» y «(2x)» no repetían; «BMW X6» se leía como «6 veces»; acentos descompuestos | reconocidos; «X6» es texto; NFC |
| Pronombres (gallego) | «en cada soño te vexo» salía «sóñote vexo» (nombres escritos como verbos) | no se juntan tras un determinante ni con «que», «non», «cando»… antes en la frase |
| Motor | si el sistema mataba la transcripción por memoria, `make` (y la cola de la GPU) esperaba para siempre | error claro de memoria |
| Motor | un paquete sin ninguna línea de letra se daba por hecho; «glg» en vez de «gl» perdía todo lo gallego | error en los dos casos |
| Vídeo | fondos verticales borrosos (406×720); el limitador subía el volumen y devolvía picos a 0 dBFS; MP4 a medias tras un fallo; rutas del paquete fuera de él | 720×1280; `level=0`; se escribe aparte y se mueve al acabar; `resolve_media` |
| Servidor | un error de SQLite (disco lleno) mataba la cola de la GPU hasta reiniciar | la cola sobrevive y sigue |
| Servidor | si el servidor moría de golpe (cerrar la terminal), su motor seguía y el siguiente arrancaba otro: dos en 4 GB | el proceso del trabajo muere con el servidor; los restos de su biblioteca se paran antes de retomar; SIGHUP apaga bien |
| Servidor | exportaciones canceladas dejaban MP4 ocultos de cientos de MB; los reintentos contaban dos veces sus fases (estimaciones más lentas) | se borran; se cuenta de cero |
| Banco | emparejaba un estribillo puntuado con su primera aparición aunque esa copia estuviese excluida: el gallego salía 98,6 % en vez de 99,8 % sobre las mismas alineaciones | se empareja contra toda la referencia |
| Banco | las canciones que fallaban desaparecían de la cobertura; el WER sin letra se medía contra la letra pegada | cuentan como palabras no colocadas; WER contra lo cantado |
| Dependencias | el motor usaba `numpy` y `ctranslate2` sin declararlos; el servidor sabía de dónde bajar los modelos | declarados; `prepare_models` vive en el motor |

## Rendimiento

`make` con letra de «un aire» (287 s): de 103–106 s a 83–87 s (−19 %), porque el audio del
paquete mide y codifica en paralelo y mientras la GPU alinea. La separación (unos 65 s) va con la
GPU al 92–100 %: acelerarla es cambiar pasadas o modelo (área C3). La letra va a 60 fps con la
CPU ×6. Informe: `bench/results/2026-11-06-c9-calidad/`. Banco sin regresiones (`quick` 99,3 %,
`gl` 99,8 %).

## Consecuencias

- `make ci` y la CI piden lo de arriba; `docs/calidad.md` explica cada puerta.
- Se quedan a propósito: volver a la fiesta con el mismo nombre recupera el turno (`010`, aunque
  otro invitado podría usarlo); sin topes de cola ni de flujos en casa; sin lista de nombres de
  `Host` (con `--open-home` una web maliciosa podría actuar como dueño); la cookie del dueño viaja
  sin cifrar por la wifi mientras no haya HTTPS en casa.
- Por debajo de lo mejor: `noUncheckedIndexedAccess` sin activar (355 errores en código correcto
  por construcción); sin pruebas de mutación; el banco aún compara ejecuciones con canciones
  distintas sin avisar, su caché no sabe del código y empareja las transcripciones solo por texto.
