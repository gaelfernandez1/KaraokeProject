import os
import re
from utils import time_str_to_sec, clean_abnormal_segments
from text_processing import normalize_manual_lyrics
import logging



# Parsea o srt e para cada bloque si hai varias lineas distribuense no intervalo. Devolvese unha lista de dicionarios: { "start": float, "end": float, "word": str }
def parse_word_srt(srt_path: str) -> list:

    segmentos = []
    if not os.path.exists(srt_path):
        print(f"non se atopou o srt {srt_path}")
        return segmentos
    with open(srt_path, "r", encoding="utf-8") as f:
        liñas = f.readlines()
    indice = 0
    while indice < len(liñas):
        liña = liñas[indice].strip()
        if liña.isdigit():
            indice += 1  
            if indice < len(liñas):
                liña_tempo = liñas[indice].strip()
                try:
                    inicio_str, fin_str = liña_tempo.split(" --> ")
                    inicio_bloque = time_str_to_sec(inicio_str)
                    fin_bloque = time_str_to_sec(fin_str)
                except Exception as e:
                    print(f"Error parseando os tempos: {e}")
                    indice += 1
                    continue
                indice += 1
                liñas_texto = []
                while indice < len(liñas) and liñas[indice].strip() != "":
                    liñas_texto.append(liñas[indice].strip())
                    indice += 1
                texto_completo = " ".join(liñas_texto)
                tokens = texto_completo.split()
                num_tokens = len(tokens)
                duracion = fin_bloque - inicio_bloque
                if num_tokens > 0:
                    duracion_token = duracion / num_tokens
                    for i, token in enumerate(tokens):
                        inicio_token = inicio_bloque + i * duracion_token
                        fin_token = inicio_token + duracion_token
                        segmentos.append({"start": inicio_token, "end": fin_token, "word": token})
                indice += 1  #salto a linea vacia
            else:
                indice += 1
        else:
            indice += 1
    
    segmentos = clean_abnormal_segments(segmentos)
    
    return segmentos


# agrupanse os segmentos de palabra en lineas e asignanse os tokens proporcionalmente respecto a cantidade esperada na
# letra manual. Asegurome de que cada linea obteña polo menos 1 token se hai polo menos unha palabra na letra.
# Devolve outra lista de diccionarios
def group_word_segments(manual_lyrics: str, word_segments: list) -> list:

    
    normalizado = re.sub(r'\n+', '\n', manual_lyrics)   #por si hai doble salto de linea deixo solo 1
    liñas = [liña.strip() for liña in normalizado.splitlines() if liña.strip()]  #Separado de lineas

    #conto cantas palabras se esperan por línea
    contador_tokens_manual = [len(liña.split()) for liña in liñas]
    total_esperado = sum(contador_tokens_manual)
    total_real = len(word_segments)

    if total_esperado == 0 or total_real == 0:
        return []

    proporcional = [ (cnt/total_esperado) * total_real for cnt in contador_tokens_manual ]

    asignados = []
    for cnt_esperado, prop in zip(contador_tokens_manual, proporcional):
        crudo = int(round(prop))
        if cnt_esperado > 0:
            #se a linea ten polo menos unha palabra, forzamos polo menos 1 token
            asignados.append(max(1, crudo))
        else:
            asignados.append(0)    #axustar para que a suma coincida con total_real
    diferencia = total_real - sum(asignados)
    decimais = [(p - round(p)) for p in proporcional]   #decimales para saber onde axustar

    while diferencia != 0:
        if diferencia > 0:
            #aumento 1 token onde o decimal sexa maior
            indice = max(range(len(decimais)), key=lambda i: decimais[i])
            asignados[indice] += 1
            decimais[indice] = 0
            diferencia -= 1
        else:  # diferencia < 0

            #disminuo 1 token onde o decimal sea mais pequeno pero sin caer por debaixo de 1 (se a liña tiña palabras claro)
            indice = min(range(len(decimais)), key=lambda i: decimais[i])
            if asignados[indice] > 1:
                asignados[indice] -= 1
                decimais[indice] = 0
                diferencia += 1
            else:
                break #se non se poden quitar mais sin romper a regla de minimo 1 salese

    #cortanse os segmentos segun os asignados e contruese o resultado
    agrupados = []
    actual = 0
    for liña, cantidad in zip(liñas, asignados):
        segmentos_parciais = word_segments[actual: actual+cantidad]
        actual += cantidad
        if segmentos_parciais:
            agrupados.append({
                "line_text": liña,
                "start": segmentos_parciais[0]["start"],
                "end": segmentos_parciais[-1]["end"],
                "words": segmentos_parciais
            })

    return agrupados
