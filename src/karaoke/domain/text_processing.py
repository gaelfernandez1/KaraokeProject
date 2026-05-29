import re
import pyphen

#pyhen é o que uso para o silabeador
dic_pyphen = pyphen.Pyphen(lang='es_ES')


def normalize_manual_lyrics(lyrics: str) -> str:
    """
    Esta funcion fixena para normalizar a letra que lle pasa o usuario, porque a veces copias e pegas tal cual da página
    de líricas e a veces ten etiquetas, saltos de linea, etc que non queres que aparezan nos subtítulos
    """
    lines = lyrics.splitlines()
    
    processed_lines = []
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
            

        line_without_tags = re.sub(r'\[.*?\]', '', line).strip()
        
        if line_without_tags:
            processed_lines.append(line_without_tags)

      # volvo a unir cun único salto de liña
    return "\n".join(processed_lines)
