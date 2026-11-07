# 016 · Repeticiones que la letra no escribe

- **Fecha**: 07/11/2026
- **Estado**: aceptada (rama `v3/repeticiones`, con el OK del dueño el 07/11/2026)
- **Afecta a**: C4 (`align/ctc.py`, `align/lyrics.py`, `align/aligner.py`, `align/pasted.py`),
  C2 (conjunto `repeats`, `karaoke-bench fetch --set repeats`)

## Contexto

Las webs de letras escriben una sola vez lo que se canta varias veces seguidas: una pareja de
versos cantada cuatro veces lleva un «(x4)» detrás de su último verso, o nada; una estrofa
cantada dos veces aparece una. La decisión 005 lo dejó pendiente («repeticiones que la letra no
dice»). El dueño lo preguntó con «II. Lisístrata» de Fillas de Cassandra, y también qué pasa con
las partes habladas (un narrador al principio o al final) que ninguna web escribe.

Con su canción, separada y alineada con su letra tal cual y con la completa:

- **Partes habladas**: se habla del segundo 1 al 17 y se canta desde el 40. El primer verso cae
  en el 40,1 s (confianza 0,96) con cualquier letra: el relleno entre versos absorbe la voz que
  no está en la letra. Lo mismo al final. No se desincroniza.
- **Repeticiones**: el «(x4)» repetía solo el último verso; sin marcas faltaban las
  repeticiones. El error se quedaba en esos tramos (versos sin pintar y un verso iluminado
  mientras se canta otro, unos 4 s con «(x4)» y unos 30 s sin marcas) y volvía a cuadrar en el
  siguiente verso distinto.
- **Más cosas del texto**: una marca delante del verso («(x3) Varre vasoira») salía como un coro
  que decía «x3», y la letra traía dos `е` cirílicas camufladas («dе», «rеi»), que algunas webs
  meten para detectar copias.

## Qué se miró

La puntuación del camino CTC de cada lectura de la misma letra sobre la misma voz (mayor es
mejor): la pareja ×4, la correcta, −2980; el verso ×4 de antes, −3067; sin repeticiones, −3193;
y una pareja de más que no se canta, −3370. El audio distingue la lectura correcta con margen y
no premia meter texto que no se canta.

Para las repeticiones sin marca, la idea del seguimiento de partituras con repeticiones (saltos
hacia atrás en la alineación, como JumpDTW): dejar que el camino vuelva a versos ya cantados.

Para medir sin tiempos hechos a mano, un conjunto nuevo, `repeats`: las 44 canciones de
JamendoLyrics que repiten versos seguidos, con la letra escrita como una web (el bloque una vez)
en dos versiones, con «(xN)» y sin marca. El audio y los tiempos no cambian, y las estrofas salen
de los ficheros de JamendoLyrics. Los ecos entre paréntesis no cuentan como repetición: las webs
los escriben.

## Decisión

1. **Texto**: la marca delante del verso repite ese verso, y las letras cirílicas o griegas que
   parecen latinas pasan a latinas en las líneas escritas en alfabeto latino (las líneas en ruso
   o griego no se tocan).
2. **Las marcas ambiguas las lee el audio**: una marca al final de un verso puede abarcar ese
   verso, los anteriores de su estrofa (2, 3, 4) o la estrofa entera. El alineador calcula la voz
   una vez y prueba cada lectura con una búsqueda del camino (lo barato); se queda con la que
   puntúa al menos 1 más que la de un verso, y prueba como mucho 24 lecturas por canción.
3. **Volver atrás dentro de la estrofa**: después de un verso, el camino puede volver al relleno
   de antes de un verso anterior de su estrofa y cantar el tramo otra vez (hasta cuatro versos
   atrás, o cualquier tramo que acabe la estrofa), pagando 30 cada vez (`repeat_penalty`). Cada
   vez sale como una línea propia.

Barrido del coste (palabras de la referencia emparejadas y a ≤ 0,3 s; techo: la letra completa
de esas canciones, 90,7 %):

| `repeats` | antes | solo lecturas | coste 15 | **30** | 60 | 120 |
|---|---|---|---|---|---|---|
| con «(xN)» | 86,2 % | 89,5 % | 89,5 % | **89,5 %** | 89,5 % | 89,5 % |
| sin marca | 78,4 % | 78,4 % | 87,8 % | **87,4 %** | 85,7 % | 83,2 % |

Con 30 se recupera cerca de tres cuartas partes de lo que se perdía. El 15 queda a 0,4 puntos,
dentro del ruido, y un coste más bajo arriesga repeticiones falsas en canciones que el banco no
tiene.

| Conjunto | antes → con 30 |
|---|---|
| `jamendo` (79, letra completa sin estrofas) | idéntico: 98,8 % a ≤ 0,3 s, media 0,093 s, cobertura 92,3 % |
| `gl` | idéntico: 99,8 % a ≤ 0,3 s |
| `quick`, `stress` | idénticos (también los grupos de ecos y adlibs) |
| privadas (4) | idénticas |
| canción del dueño, letra con «(x4)» | 45 → 49 de 50 versos a ≤ 0,3 s |
| canción del dueño, sin marcas | 39 → 47 de 50 |

En ningún conjunto empeora ninguna canción. Tiempo: con letra sin marcas ambiguas el alineador
tarda un 12 % más (unos 0,4 s en 4 min); con marcas ambiguas, unos 6 s más por probar lecturas.
Informes en `bench/results/2026-11-07-repeticiones-*`.

## Consecuencias

- `LyricLine.stanza` y `parse_lyrics(text, scopes)`/`repeat_marks(text)` son nuevos;
  `align_segments` admite `repeat_penalty` y `Segment.group`, y `best_path` devuelve también la
  puntuación. `SegmentPath.repeats` trae cada vez que un verso se vuelve a cantar.
  `LyricsAligner.version` = 14.
- No se recupera un estribillo escrito una vez al principio y cantado otra vez más adelante sin
  nombrarlo: la vuelta atrás solo repite lo que va justo antes, dentro de la misma estrofa (para
  volver a donde estaba haría falta memoria, que una búsqueda así no tiene). Si la web lo nombra
  («[Estribillo]», «Repetir coro»), ya se repite.
- Las partes habladas que no están en la letra no se pintan; el relleno las absorbe. Una palabra
  muy corta y poco clara al principio de la letra puede saltar a ellas (pasó en la demo
  «laverca»), pero no arrastra al resto.
