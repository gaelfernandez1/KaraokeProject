# Plan v3 · Prompts de las conversaciones

Cómo arrancar cada conversación: abre Claude Code en `/home/gaelbl/KaraokeProject` y pega la línea
de arranque de esa conversación, por ejemplo:

```
Eres la conversación C1 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C1») y síguelo.
```

Si una conversación se corta o se alarga, se retoma igual en otra nueva: `ESTADO.md` dice por dónde
iba. Orden recomendado en `00-vision.md` §9.

---

## Bloque común (vale para todas)

Eres una de las conversaciones del plan v3 del KaraokeProject. Antes de nada lee, en este orden:
`CLAUDE.md`, `docs/plan-v3/00-vision.md` (objetivo, principios, arquitectura, contratos y reparto),
`docs/plan-v3/ESTADO.md` (qué han hecho las demás) y `docs/plan-v3/decisiones/`. Lo que dice
`00-vision.md` manda sobre cualquier documento antiguo (plan v2, `docs/00–10`, `STATE.md`).

**Objetivo del usuario**: una mejora masiva de todo el proyecto, con libertad total para cambiar
cómo se hace mientras se mantenga el objetivo: un karaoke que funcione en muchos idiomas pero sobre
todo en gallego, bien transcrito, con subtítulos animados que vayan al mismo tiempo que se canta.
Debe funcionar con cualquier canción y en cualquier contexto (móvil, portátil y tele por HDMI), con
un sonido que funcione bien en todo y tenga algo chulo. Da igual cómo se haga: si algo no tiene
sentido, se hace de otra forma mejor. Usa las herramientas más potentes de hoy.

**Reglas**:

1. **Modelo**: usa siempre Opus, también en subagentes (no les pongas otro modelo). Si se acaba
   la cuota, para y espera; no cambies de modelo.
2. **Autenticaciones**: si algo necesita login, token, clave o sudo, para y pídeselo al usuario;
   él se autentica a mano.
3. **Proceso**: `superpowers:brainstorming` corto sobre lo específico de tu área (lo general ya
   está decidido en `00-vision.md`: no lo vuelvas a preguntar) → `superpowers:writing-plans` →
   ejecución (`superpowers:subagent-driven-development` o `superpowers:executing-plans`) con
   `superpowers:test-driven-development` → `/code-review` → `superpowers:verification-before-completion`
   → PR con `superpowers:finishing-a-development-branch`.
4. **Investiga** lo que haga falta de tu área (web, documentación actual vía Context7 si está) antes
   de elegir. Las pistas de `00-vision.md` §7 son un punto de partida, no una obligación.
5. **Mide** con el banco (skill `probar-karaoke`, cuando exista) todo lo que afecte a la calidad o
   la velocidad, y deja el informe en `bench/results/`.
6. **Git**: trabaja en la rama `v3/c<N>-<tema>` (en un worktree si hay otra conversación activa y
   C1 ya terminó). Commits en inglés con tono humano. **Nunca commit ni push sin el OK explícito
   del usuario.** `main` siempre verde.
7. **Límites**: toca solo tu área (tabla de `00-vision.md` §8). Si necesitas cambiar un contrato o
   algo de otra área, escribe una decisión en `docs/plan-v3/decisiones/` y anótalo en `ESTADO.md`
   para la conversación afectada.
8. **Estado**: tras cada hito, actualiza tu fila de `ESTADO.md` (hecho, interfaces que expones,
   pendiente para otras). Si aprendes algo del usuario, guárdalo en la memoria.
9. **Habla con el usuario en español**, en lenguaje claro (no es experto en hardware: pasos físicos
   detallados). El código, los comentarios y los commits van en inglés; la interfaz, en gallego,
   castellano e inglés.

---

## C1 · Arquitectura, repo y cimientos

**Línea de arranque**: `Eres la conversación C1 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C1») y síguelo.`

**Misión**: dejar el terreno listo para que C2–C10 trabajen, a veces en paralelo, sin pisarse:
estructura, herramientas, contratos y repo.

**Incluye**:
- Revisar las decisiones iniciales de `00-vision.md` §5 con una investigación breve y confirmarlas
  o cambiarlas con decisiones escritas (`001-…`).
- Git y GitHub: decidir con el usuario qué hacer con `feature/f13-deploy` y las ramas viejas;
  etiquetar el estado legado; estrategia de ramas `v3/…` y PRs. Hacer que `docs/plan-v3/`,
  `CLAUDE.md` y `.claude/skills/` se versionen (ajustar `.gitignore` y revisar antes que no haya
  secretos). Archivar los documentos viejos en `docs/archivo/`.
- `CLAUDE.md` nuevo y corto (≤ 100 líneas): qué es, estructura, comandos, reglas y punteros a
  `plan-v3`. Actualizar las memorias del proyecto que hayan quedado viejas.
- Estructura del monorepo (motor, servidor, web, esquemas, banco y lo viejo apartado sin romperlo,
  o la alternativa que justifiques).
- Herramientas: uv + Python 3.12, ruff, comprobador de tipos, pytest, pre-commit; Node 22 y gestor
  de paquetes para la web; tareas comunes (just o make); CI de GitHub Actions básica (lint, tipos,
  tests en CPU, build de la web).
- Entorno de desarrollo en WSL con GPU: torch con CUDA funcionando, ffmpeg (con libass y NVENC si
  es posible) y una guía de instalación reproducible.
- Contratos v0 (`00-vision.md` §6): modelos pydantic + JSON Schema de `karaoke.json` y
  `theme.json`, tipos TS generados, tipo del reloj `now()`, interfaces de los pasos del motor,
  validador, tests y un paquete de ejemplo sintético (audio generado + tiempos) para que C5 y C7
  puedan empezar sin el motor.
- Comodidades de Claude Code: hook de formateo tras editar, MCPs recomendados (Context7,
  Playwright; arreglar GitHub o instalar `gh`), permisos habituales (skill `fewer-permission-prompts`).

**No incluye**: elegir modelos (C3, C4) ni implementar el motor, la web o el servidor.

**Depende de**: nada; va la primera y sola.

**Pregunta al usuario**: qué hacer con la rama f13 y con la infraestructura vieja (R2, Fly, Sentry,
magic links); si el repo sigue público; si quiere cambiar el nombre del proyecto.

**Hecho cuando**: `uv sync`, tests y lint en verde en local y en CI; torch ve la GPU en WSL; ffmpeg
funciona; esquemas con tests y paquete de ejemplo válido; `CLAUDE.md` y `plan-v3` versionados;
`ESTADO.md` al día; PR mergeado con el OK del usuario.

---

## C2 · Banco de pruebas y métricas

**Línea de arranque**: `Eres la conversación C2 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C2») y síguelo.`

**Misión**: poder decir con números si cada cambio mejora la transcripción, la sincronía y la
velocidad, con canciones variadas y sobre todo en gallego, para que funcione con cualquier canción.

**Incluye**:
- Conjunto público: JamendoLyrics MultiLang / Jam-ALT (CC, tiempos por palabra en en/es/fr/de),
  descargado por script (el audio no se commitea).
- Conjunto gallego: buscar en internet canciones en gallego con licencia CC (Jamendo, Internet
  Archive, Wikimedia Commons, Bandcamp con CC…) y su letra. Variedad: estilos (folk y pandeireta,
  pop, rock, rap y trap, coros, dúos), voces, tempos y calidad de grabación; también alguna en
  portugués y en castellano.
- Referencias de tiempos para el gallego: generarlas de forma semiautomática y que el usuario
  valide o corrija de oído un subconjunto, con la herramienta más cómoda para él (p. ej. Aegisub o
  una página mínima de comprobación).
- Hueco para canciones privadas del usuario: solo en local y fuera de git.
- Métricas: WER y CER (con normalización de texto gallego), error de inicio y fin de palabra
  (mediana, media, % ≤ 0,3 s), tiempo de proceso, VRAM pico y cambios de idioma.
- Runner (`karaoke bench` o equivalente) que acepta cualquier combinación de pasos del motor
  (interfaces de C1), con informes markdown comparables en `bench/results/`.
- Línea base: medir lo que sea viable (el pipeline viejo si no cuesta mucho, o las opciones por
  defecto del motor nuevo) y fijar las metas definitivas de `00-vision.md` §1 con una decisión
  escrita.
- Skill de proyecto `probar-karaoke` (con `superpowers:writing-skills` o `skill-creator`) para que
  cualquier conversación ejecute el banco igual.
- Convertir 2–3 canciones públicas con tiempos de referencia en paquetes de karaoke de ejemplo
  (audio descargado por script), para que C5 y C7 trabajen con canciones reales.

**No incluye**: elegir ni optimizar modelos (C3, C4).

**Depende de**: C1.

**Pregunta al usuario**: si quiere añadir canciones suyas y cuáles; cuánto tiempo puede dedicar a
validar de oído.

**Hecho cuando**: `probar-karaoke` produce un informe reproducible con al menos 20 canciones
públicas y las gallegas que se acuerden con el usuario (con referencias validadas); metas fijadas;
documentado cómo añadir canciones.

---

## C3 · Audio: separación y sonido

**Línea de arranque**: `Eres la conversación C3 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C3») y síguelo.`

**Misión**: la mejor separación entre voz e instrumental que quepa en 4 GB de VRAM y un sonido que
funcione bien en el móvil, el portátil y la tele, con algo chulo.

**Incluye**:
- Separación con modelos actuales (BS-RoFormer o Mel-Band RoFormer vía audio-separator u otra vía);
  probar un modelo karaoke (voz principal frente a coros) y quitar reverberación si mejora la
  alineación. Elegir con el banco (efecto en la sincronía y el WER, escucha, tiempo y VRAM). Como
  C4 aún no existe, mide la sincronía con un alineador provisional (p. ej. WhisperX 3.8 con su
  modelo por defecto) y deja anotado en `ESTADO.md` que C4 revalide la elección con su alineador.
- Ingesta: decodificar cualquier formato con ffmpeg, remuestrear y normalizar el volumen (EBU R128)
  para que todas las canciones suenen igual.
- Formatos del paquete aptos para todos los navegadores (Safari incluido), con salto rápido.
- Motor de audio del reproductor (módulo TS de la web): instrumental y voz guía sincronizadas con
  volumen de voz regulable, cambio de tono (con licencia compatible), compensación de latencia
  (HDMI y Bluetooth) con una calibración sencilla, reloj `now()` para la letra y memoria razonable
  en móviles.
- Proponer y, si el usuario quiere, hacer extras chulos: micrófono con eco o reverb por el
  portátil, guía de melodía o puntuación por afinación, efectos de entrada y salida, etc.

**No incluye**: la interfaz de los controles (la integra C7) ni la transcripción (C4).

**Depende de**: C1 y C2.

**Pregunta al usuario**: cómo canta (con micro o sin él, por qué altavoces) y qué extras de sonido
le ilusionan más.

**Hecho cuando**: separación elegida con datos del banco; paquete con audio normalizado; motor de
audio con tests y probado en móvil y portátil; latencia ajustable; `ESTADO.md` al día.

---

## C4 · Transcripción y sincronización (gallego primero)

**Línea de arranque**: `Eres la conversación C4 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C4») y síguelo.`

**Misión**: que la letra sea correcta y cada palabra (y parte de palabra) tenga su tiempo real; en
gallego al nivel de los idiomas grandes, y bien en muchos otros idiomas. Es la conversación más
importante para el objetivo.

**Incluye**:
- Idioma: lo elige el usuario (gallego por defecto); la detección solo sugiere; nunca un cambio
  silencioso de idioma; si falta un recurso para el idioma, usar el mejor disponible y anotarlo en
  `provenance`.
- Con letra dada: normalizarla solo para alinear (etiquetas como [Estribillo], repeticiones "x2",
  números a palabras en gallego, apóstrofos y contracciones, ortografía reintegracionista y
  dialectal: ç, nh, lh, gheada…) y mostrar siempre el texto original.
- Sin letra: transcripción con el mejor modelo por idioma (para gallego, candidatos de Nós, HiTZ y
  BSC; para el resto, Whisper large-v3-turbo u otro mejor), con VAD sobre la voz separada y
  salvaguardas contra alucinaciones; opción de buscar la letra en LRCLIB.
- Alineación forzada con modelo por idioma (para gallego, comparar los CTC de Nós con `ifrz` y
  otros), tiempos por palabra y por carácter, confianza por palabra y recuperación en tramos
  difíciles (instrumentales largos, repeticiones, coros, palabras que no alinean).
- Segmentación en líneas: de la letra si existe; si no, por pausas, puntuación y longitud.
- Subunidades (`parts`): sílabas si aportan (pycotovia o reglas gallegas) o grupos de letras con
  tiempos reales; decidir con C5 qué se ve mejor.
- Dúos o varias voces (diarización) como mejora opcional al final.
- Elegir modelos con los números del banco; respetar los 4 GB de VRAM (un modelo a la vez,
  int8/float16).

**No incluye**: la separación (C3) ni cómo se pinta la letra (C5).

**Depende de**: C1, C2 y C3 (voz separada).

**Pregunta al usuario**: de dónde suele sacar las letras; si canta canciones en norma
reintegracionista o con variantes dialectales; si le importan los dúos.

**Hecho cuando**: `karaoke make` produce un `karaoke.json` válido; metas de sincronía y de WER del
banco alcanzadas o explicadas; el gallego no cae a otro idioma en ninguna canción del banco;
tiempos de proceso dentro de la meta.

---

## C5 · Subtítulos animados

**Línea de arranque**: `Eres la conversación C5 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C5») y síguelo.`

**Misión**: que la letra se vea preciosa y se ilumine exactamente al ritmo del canto, igual en el
navegador que en el MP4.

**Incluye**:
- Diseño del movimiento: qué se ve (línea actual y siguiente, páginas), cómo entra y sale, cómo se
  rellena (barrido continuo con tiempos por carácter, sílabas, palabra a palabra…), cuenta atrás
  antes de volver a cantar tras un instrumental, colores por cantante y legibilidad en móvil
  vertical, portátil y tele a 3 m. Enseñar opciones al usuario (maquetas o prototipos) y elegir
  con él.
- Temas (`theme.json`): varios (p. ej. clásico de karaoke, moderno, alto contraste), con fuentes de
  licencia libre y buen soporte de diacríticos.
- Componente web de letra (TS) a 60 fps, sincronizado con el reloj `now()` del motor de audio y
  adaptable a cualquier pantalla.
- Generador ASS en Python a partir del mismo `karaoke.json` + tema (`\kf` y efectos; PyonFX si
  ayuda), que C6 usa para el MP4, con un aspecto lo más parecido posible al de la web.
- Pruebas: capturas visuales con Playwright, tests del generador ASS y comparación lado a lado
  entre web y MP4.

**No incluye**: fondo y codificación del vídeo (C6), el resto de la app (C7) ni los tiempos (C4).

**Depende de**: C1 (esquema y paquete de ejemplo). Puede empezar en paralelo a C2–C4.

**Pregunta al usuario**: karaokes o apps de letras que le gusten (referencias visuales) y qué le
molesta de los actuales.

**Hecho cuando**: componente web y generador ASS comparten tema; el usuario los aprueba en su
móvil, su portátil y su tele; hay tests.

---

## C6 · Vídeo

**Línea de arranque**: `Eres la conversación C6 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C6») y síguelo.`

**Misión**: fondos bonitos y una exportación MP4 rápida y de calidad para la tele y las redes.

**Incluye**:
- Fondos: vídeo original (oscurecido o desenfocado, configurable), portada o imagen con movimiento
  suave, fondos generados (degradados, visualizador de audio) e imágenes del usuario.
- Vídeo de fondo para el reproductor web: transcodificación apta para web, saltos rápidos y
  sincronía con el audio.
- Exportación MP4: fondo + ASS de C5 + audio (instrumental, con voz guía opcional) con
  ffmpeg/libass y NVENC si está; 16:9 (1080p) y 9:16; pantalla de título y créditos o licencias;
  portada y miniatura.
- Rendimiento medido (meta: 1080p de 4 min en ≤ 1 min) y retirada de MoviePy, PIL e ImageMagick.

**No incluye**: el diseño de los subtítulos (C5) ni el audio (C3).

**Depende de**: C1, C5 (generador ASS) y C3 (formatos de audio).

**Pregunta al usuario**: qué fondo prefiere por defecto y si quiere formato vertical para redes.

**Hecho cuando**: `karaoke render` exporta 16:9 y 9:16 dentro de la meta; el fondo del reproductor
web está listo; hay tests.

---

## C7 · Frontend (web, móvil y modo TV)

**Línea de arranque**: `Eres la conversación C7 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C7») y síguelo.`

**Misión**: una app web cuidada que funcione igual de bien en el móvil, el portátil y la tele por
HDMI.

**Incluye**:
- Diseño visual y sistema de diseño (skill `frontend-design`); gallego, castellano e inglés con
  gallego por defecto; accesibilidad.
- Flujos:
  - Crear karaoke: subir archivo o enlace, idioma con gallego por defecto, letra opcional y progreso
    en vivo.
  - Biblioteca: buscar y filtrar.
  - Reproductor: integra la letra de C5, el audio de C3 y el fondo de C6.
  - Modo TV: pantalla completa, letra grande, márgenes seguros, manejo con teclado o mando y
    pantalla siempre encendida.
  - Modo fiesta: un QR para que los móviles busquen, añadan a la cola y hagan de mando (voz guía,
    tono, pausa).
  - Editor de letra y sincronía: corregir palabras y tiempos, y marcar el ritmo tocando la pantalla
    para resincronizar una línea.
  - Descarga del MP4 y de las pistas.
- PWA: instalable y, si es viable, con las canciones guardadas disponibles sin conexión.
- Cliente de la API generado desde OpenAPI (C8); mientras C8 no esté, datos de ejemplo o mocks.
- Pruebas de extremo a extremo con Playwright en tamaños de móvil, portátil y tele.

**No incluye**: el componente de letra (C5) ni el motor de audio (C3); los integra.

**Depende de**: C1; integra C3, C5, C6 y C8 según vayan llegando.

**Pregunta al usuario**: apps que le gusten, cómo se imagina la fiesta y qué debe poder hacer el
móvil.

**Hecho cuando**: todos los flujos funcionan de extremo a extremo con el servidor real y el usuario
los aprueba en su móvil, su portátil y su tele.

---

## C8 · Backend, servidor y despliegue

**Línea de arranque**: `Eres la conversación C8 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C8») y síguelo.`

**Misión**: un servidor sencillo y fiable que procese en la GPU del portátil y sirva los karaokes a
cualquier dispositivo, en casa y fuera.

**Incluye**:
- API (FastAPI salvo decisión contraria) con OpenAPI.
- Cola de trabajos para una GPU, con progreso en vivo (WebSocket o SSE), cancelación y reintentos.
- Biblioteca: base de datos y archivos de los paquetes.
- Subidas grandes con validación de tamaño, duración y formato; descarga por enlace con yt-dlp
  actualizado como opción best-effort.
- Usuarios y acceso: el propietario y los invitados de la fiesta (QR o enlace temporal), sin
  complicarlo. Decidir con el usuario qué se queda de lo viejo (magic links, allowlist, R2, Sentry,
  Fly).
- Red:
  - URL y QR en la red de casa.
  - Acceso desde fuera con túnel gratuito (Tailscale o Cloudflare Tunnel).
  - Si se decide, reproducción de las canciones ya hechas desde almacenamiento gratuito en la nube,
    con el portátil apagado.
- Arranque fácil: un comando o un servicio al iniciar Windows/WSL. Docker para desplegar si aporta,
  logs estructurados y copias de seguridad de la biblioteca.
- Migrar o descartar (con el usuario) los karaokes de la base de datos vieja.

**No incluye**: la lógica del motor (C3, C4) ni la interfaz (C7).

**Depende de**: C1, y del motor con CLI (C3, C4) para el worker.

**Pregunta al usuario**: quién más lo usará; si quiere usarlo fuera de casa; si quiere las
canciones disponibles con el portátil apagado.

**Hecho cuando**: desde el móvil, en la red de casa, se crea un karaoke y se canta en la tele;
acceso remoto si se eligió; tests de la API y de la cola.

---

## C9 · Calidad de código (transversal)

**Línea de arranque**: `Eres la conversación C9 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C9») y síguelo.`

**Misión**: que todo el código sea coherente, limpio, tipado, probado y sin restos del sistema
viejo.

**Incluye**:
- Auditoría completa por áreas con `/code-review` y `/simplify`.
- Borrar lo apartado como viejo y las dependencias muertas (MoviePy, ImageMagick, el servicio
  whisperx, Celery y Redis si ya no se usan).
- Tipos estrictos y cobertura de tests en lo crítico: contratos, alineación, generador ASS y API.
- Coherencia de nombres y de manejo de errores.
- Perfilado de rendimiento del motor y de la web.
- Auditoría de dependencias y de seguridad (`/security-review`), y comprobar que el código respeta
  los contratos.

**No incluye**: funcionalidades nuevas.

**Depende de**: C2–C8 terminadas o casi.

**Hecho cuando**: CI en verde con reglas estrictas; sin código muerto; informe de auditoría con lo
arreglado; banco sin regresiones.

---

## C10 · Proyecto profesional

**Línea de arranque**: `Eres la conversación C10 del plan v3. Lee docs/plan-v3/01-conversaciones.md («Bloque común» y «C10») y síguelo.`

**Misión**: que el repositorio parezca y funcione como un proyecto open source serio.

**Incluye**:
- README en gallego (con versiones en castellano e inglés), con demo en GIF y capturas, y guía de
  instalación de un comando.
- Documentación: arquitectura a partir de las decisiones, cómo añadir idiomas o modelos y cómo
  contribuir.
- Ficheros de comunidad: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY y plantillas de issues y PR.
- Licencias de terceros y de modelos (NOTICE), CITATION.cff y referencia al TFG.
- Publicación: versionado semántico, CHANGELOG y releases en GitHub.
- Mantenimiento del repo: Dependabot o Renovate, protección de rama, insignias y ajustes (descripción
  y temas).
- Karaoke de demostración con una canción CC; opcionalmente, una web de documentación.

**Depende de**: C9.

**Pregunta al usuario**: nombre y marca, si quiere logotipo e idioma principal del README.

**Hecho cuando**: release v3.0.0 publicada (con el OK del usuario) y el repo con todo lo anterior.
