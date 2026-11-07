# 015 · La letra se pega tal cual viene de la web

- **Fecha**: 07/11/2026
- **Estado**: aceptada (rama `v3/letra-pegada`, con el OK del dueño el 07/11/2026)
- **Afecta a**: C4 (`karaoke_engine.align.pasted` nuevo; `parse_lyrics` y `make_package` lo usan),
  C7 (texto de ayuda de la letra en «Crear»)

## Contexto

El dueño copia las letras de webs como Genius y quiere que cualquiera pueda pegarlas sin
retocar nada. `parse_lyrics` ya quitaba las cabeceras entre corchetes (`[Verso 1: Ana]`), las
repeticiones y los estribillos solo nombrados, pero lo demás que trae la página acababa cantado:
con una letra suya copiada de Genius se colaban siete líneas del bloque «You might also like»
(tres canciones recomendadas, con su título y su artista), y el alineador tenía que colocarlas en
el audio.

## Qué se miró

Lo que deja en el portapapeles cada sitio habitual: Genius (recomendaciones y anuncios de
entradas en mitad de la letra, colaboradores, traducciones, título, descripción con «Read More»,
«Embed» final), Musixmatch y el cuadro de letras de Google («Writer(s):», «Fuente: Musixmatch»,
«©»), Letras («Composição:», «Enviada por…»), AZLyrics, descripciones de vídeos (créditos,
redes, enlaces, hashtags), webs en castellano y portugués (etiquetas sin corchetes: «CORO:»,
«(Estribillo x2)», «Repetir coro», duetos con «Él:»/«Ella:»), y letras con tiempos (SRT, LRC,
transcripciones de YouTube).

## Decisión

Un paso nuevo, `strip_page_text`, limpia el texto antes de leerlo. Es conservador: una línea se
quita solo cuando ninguna canción la cantaría. Lo que podría ser letra («Solo», «Ponte guapa»,
«Letra de amor») solo se quita encima o debajo de la letra, o nunca. Las etiquetas sin corchetes
se reescriben como cabeceras para que `parse_lyrics` las entienda igual; «Repite el coro» trae el
último estribillo aunque se llamase `[Estribillo]`. Las acotaciones entre paréntesis («(risas)»,
«(hablado)») se quitan salvo que la línea cante esa palabra como eco («Pon a música (música)»).
`make_package` conoce el título y el artista, así que también quita las líneas de encima que
solo nombran la canción (si una canción empieza cantando su título, se deja).

## Consecuencias

- Con la letra de Genius del dueño, sin tocar, salen exactamente las 48 líneas de su versión
  retocada a mano, con los cantantes de cada parte.
- En las 107 letras del banco (JamendoLyrics, gallegas, `stress` y privadas) el resultado de
  `parse_lyrics` es idéntico al de antes: las cifras del banco no cambian. `LyricsAligner.version`
  pasa a 13 para no reutilizar la caché.
- Una línea cantada que sea solo una etiqueta («Intro», «Coro») se toma por etiqueta.
- Si Genius enseña menos de tres recomendaciones y la letra sigue sin cabecera ni línea en blanco,
  se pueden perder hasta dos líneas cantadas; no se vio nunca.
