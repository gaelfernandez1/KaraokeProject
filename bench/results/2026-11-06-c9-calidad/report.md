# Calidad de código · velocidad de `make` y regresión del banco

- Fecha: 2026-11-06
- Equipo: RTX 3050 Laptop (4 GB), Ryzen 7 5800H, WSL 2 con unos 7,6 GB de RAM, portátil enchufado
- Código: rama de calidad sobre `main` `bff0ef9`

## `make` con letra: audio del paquete en paralelo y solapado con la alineación

Canción: «un aire» (Pantis, 287 s, FLAC, conjunto `gl`), con su letra. Antes, el paso de audio
del paquete medía la sonoridad tres veces y codificaba dos m4a uno tras otro, después de alinear.
Ahora mide y codifica a la vez, y empieza en cuanto termina la separación, mientras la GPU alinea
(o transcribe). Mismo código en las dos variantes: la «antes» sustituye los ejecutores en
paralelo por uno en serie. Una ejecución cada vez, alternando.

| Variante | Pasada 1 | Pasada 2 | Separar | Alinear | Espera del audio |
|---|---|---|---|---|---|
| antes (en serie, tras alinear) | 106,0 s | 103,4 s | 94–96 s (incluye el audio) | 9–10 s | — |
| ahora (en paralelo, solapado) | 86,9 s | 82,7 s | 64–68 s | 12–14 s | 4–5 s |

Unos **20 s menos (−19 %)**; para 4 min, unos 71 s (meta: ≤ 2 min). La alineación tarda algo más
porque comparte la CPU con ffmpeg. El servidor estima la fase de audio con los valores nuevos
(`jobs/progress.py`).

## Separación: la GPU va a tope

Muestreo de `nvidia-smi` cada 0,5 s durante una pasada: con un modelo cargado, uso medio de la GPU
del **92 %** (mediana 100 %), VRAM pico **2,87 GB**. La separación (unos 65 s para 287 s) está
limitada por la GPU: acelerarla pide menos pasadas solapadas o otro modelo, que es una decisión de
calidad del área de audio. Queda como propuesta, sin tocar.

## Regresión del banco (con letra)

Pipeline `c4-default` (el de `karaoke make`), con dos nombres para distinguir las pasadas:

- `c9-antes`: alineador v11, alineaciones de la caché (código anterior), puntuadas con las métricas
  corregidas.
- `c9-despois`: alineador v12, realineado con el analizador de letras nuevo (marcas «2x» y tras la
  cabecera, NFC, «X6» como texto).

| Conjunto | ≤ 0,3 s antes | ≤ 0,3 s después | Mediana | Cobertura | Canciones que empeoran |
|---|---|---|---|---|---|
| `quick` (20) | 99,3 % | 99,3 % | 0,032 s | 94,1 % | ninguna |
| `gl` (5) | 99,8 % | 99,8 % | 0,020 s | 100 % | ninguna |

El cambio del analizador no mueve ninguna palabra de estos conjuntos (no traen esas marcas).

### Efecto de las métricas corregidas

Sobre las mismas alineaciones, el informe del 29/10 (`2026-10-29-c4-default-gl-lyrics`) daba en
`gl` un **98,6 %** a ≤ 0,3 s y ahora sale **99,8 %**. La diferencia es del banco, no del motor:
emparejaba las palabras puntuadas de un estribillo con la primera vez que se canta aunque esa
copia estuviese excluida («unsure»). `quick` no cambia (todas sus líneas cuentan). Otras dos
correcciones del banco no afectan a estas pasadas: las canciones que fallan ya cuentan sus
palabras como no colocadas (cobertura) y el WER sin letra se mide contra lo cantado, no contra la
letra pegada.

Informes: `bench/results/2026-11-06-c9-antes-{quick,gl}-lyrics/` y
`bench/results/2026-11-06-c9-despois-{quick,gl}-lyrics/`.
