# 017 · Rediseño «Noite»: Galicia de noche en su propio planeta

- **Fecha**: 07/11/2026 (primera versión), rehecho el 12–13/11/2026
- **Estado**: hecho a falta del OK del propietario (rama `v3/noite`); se aprueba con su PR
- **Sustituye**: la dirección visual «Cartaz» de `010-frontend.md` (el resto de 010 sigue en pie:
  framework, i18n, SSE, turnos, servidor simulado, sin conexión)
- **Afecta a**: solo la web (área de frontend). No cambia contratos, API ni el motor.

## Contexto

El propietario no está a gusto con el diseño de carteles. Pide un menú principal con un globo
terráqueo nocturno, como el de los menús de los shooters de hace una década (el mundo de noche con
luces donde hay jugadores conectados), pero con Galicia: estética de noche y las luces reales de
Galicia según dónde vive la gente. La referencia no debe notarse demasiado. El resto queda a
criterio del área.

Hubo una primera versión (07/11): un disco plano con un mar de puntos que giraba mientras Galicia
se quedaba quieta, tipografía condensada con cifras de puntos y listas como paneles de salidas.
El propietario la descartó al verla: el globo y el contorno le parecieron poco elaborados y las
secciones, demasiado simples; que el borde gire y Galicia no, «no queda bien»; los puntitos no le
convencen; y pidió cambiar tipografías, estilos y paleta. Esta decisión recoge la versión rehecha.

## Qué se miró

- **Datos**. Luces: Kontur Population 2023 (personas por hexágono H3 de 400 m, CC BY 4.0, vía
  HDX): 23 419 celdas habitadas en Galicia que suman 2 762 451 personas. Relieve y costa: teselas
  de elevación de Mapzen en AWS Open Data (SRTM y EU-DEM en tierra, ETOPO1 en el mar), a unos
  220 m por píxel: la costa sale del propio relieve, con las rías y las islas, mucho más fina que
  la de Natural Earth, que solo decide qué es Galicia y qué es Asturias, León, Zamora o Portugal.
  Faros: Wikidata (CC0) trae 27 en la costa gallega con su posición, su característica de carta
  («Fl(4) W 20s»: cuatro destellos cada veinte segundos) y su alcance en millas. VIIRS (luces de
  satélite) pide cuenta de NASA y resuelve peor; el nomenclátor del IGN tenía la descarga caída.
- **Globo**. Librerías 3D (three.js y similares) cuestan 150 kB o más; un planeta con relieve,
  mar, luces y haces se dibuja con WebGL 2 en unos cientos de líneas (unos 12 kB). Galicia a
  escala real sería una mota en la Tierra: se dibuja agrandada como único continente de un
  planeta pequeño.
- **Movimiento**. Lo que no convencía era la incoherencia (mar que gira, tierra quieta). Un
  planeta sólido que se mueve entero no la tiene: un balanceo lento mantiene Galicia siempre a la
  vista, y el relieve, las luces y los haces de los faros cambian con la perspectiva.
- **Peso y cadencia**. Con gráficos por software (la CI, equipos sin GPU) un lienzo a pantalla
  completa retrasaba hasta la navegación. El lienzo cubre solo el globo, baja de resolución y de
  cadencia cuando los fotogramas llegan tarde, espera mientras cambia la página y no dibuja si el
  globo no se ve.

## Decisión

- **Mundo**: un planeta pequeño de noche donde Galicia es la única tierra, en 3D: relieve real
  iluminado por la luna (con curvas de nivel cada 200 m), costa nítida con las aguas someras
  encendidas, límites de provincia, las luces de los pueblos como resplandores (como una foto
  nocturna de satélite) y los faros barriendo el mar con su ritmo y su alcance reales. Todo el
  planeta se mueve como una sola pieza: se balancea despacio y se puede coger y girar; al
  soltarlo, vuelve. La primera vez de cada visita llega girando desde mar abierto y las luces se
  encienden, ciudades primero; con movimiento reducido está ya encendido y quieto. Un botón lo
  para (WCAG 2.2.2) y el aparato lo recuerda.
- **Un globo para toda la app**: un lienzo fijo bajo todas las pantallas, montado una vez en el
  layout. Cada pantalla dice dónde lo quiere con un ancla y el globo vuela hasta allí. Enseña de
  qué va la pantalla: en la fiesta, anillos con los colores de quien canta y cohetes; en crear,
  las luces se encienden desde el oeste hasta donde va el karaoke; en ajustes, pasan al frente
  los meridianos y las curvas de nivel.
- **Menú limpio** (13/11, a petición del propietario): solo el planeta y el menú. Se quitaron
  los instrumentos de debajo (personas y luces, amanecer o anochecer, luna, faros nombrados de
  uno en uno con su anillo en el globo), la hora en Santiago y la luna de arriba, y el rótulo del
  mar Cantábrico. La versión anterior queda en la rama local `v3/noite-respaldo`.
- **Color**: mar y cielo casi negros con un punto de azul (`#04070c`); blanco para las palabras
  y para la acción principal de cada pantalla; el celeste de la bandera `#5cc8ff` = seleccionado
  y foco (y la costa en el globo); el dorado de una ventana encendida `#ffd38a` = lo que está en
  marcha: lo cantado, lo de ahora, las luces. Los colores de cantante (personas) no son ni
  dorado ni celeste.
- **Tipografía**: Unbounded (OFL), ancha y redonda, para el menú, los títulos y los nombres;
  Figtree (OFL) para el texto; Martian Mono (OFL) para las cifras que se miden o se leen en voz
  alta (horas, tiempos, el código de la fiesta). Sin mayúsculas en etiquetas.
- **Formas**: todo redondeado; botones y nombres de persona en píldora; lo que flota sobre el
  globo es un panel translúcido que deja ver la noche. Sin puntos, sin filas cuadradas.
- **Canciones**: una lista y, al lado, grande, la canción señalada: portada, la frase que todo
  el mundo conoce, sus datos y qué hacer con ella. Sin portada, cada canción tiene su propio
  cielo (dos luces suaves cuyos colores salen de su identificador) con su inicial.
- **Datos en el repo**: `scripts/galicia_map.py` (dependencias en la cabecera, se ejecuta con
  `uv run`) genera `web/src/lib/globe/galicia.ts` (contorno para el dibujo fijo, ciudades, faros
  y totales) y `galicia-map.bin` (163 kB: relieve, luces y provincias en una rejilla de 0,45 km,
  comprimida).

## Consecuencias

- El motor del globo y su mapa se cargan después de la primera pintura y solo si una pantalla
  pide el globo; un contorno fijo en SVG sale al instante y se queda donde no hay WebGL. La
  portada carga 99 kB de JavaScript (presupuesto: 120).
- `NOTICE.md` acredita Kontur (CC BY 4.0), Natural Earth, las teselas de relieve (SRTM, EU-DEM,
  ETOPO1), Wikidata y las fuentes nuevas (OFL).
- La pantalla completa de la fiesta es la del documento entero, no la de su pantalla: el lienzo
  del globo vive fuera de ella.
- Desaparecen `Poster.svelte`, `Swatch.svelte`, `poster/style.ts` y `ui/SungText.svelte`;
  `Cover.svelte` hace de portada en todas partes y los colores de persona salen de un solo sitio
  (`party/colors.ts`).
- Las rejillas de una columna llevan `minmax(0, 1fr)`: sin eso, un campo o un título largo
  ensanchaba la página en el móvil.
- Las capturas y la animación del README se rehacen con `web/dev/readme-media.mjs`
  (`screens/menu.png` sustituye a `library.png`); el icono y los banners, con `web/dev/icons.mjs`
  y `web/dev/brand.mjs`.
