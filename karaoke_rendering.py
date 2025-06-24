import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip
from config import (
    TEXT_CLIP_WIDTH, FONTE, TAMAÑO_FONTE, TAMAÑO_FONTE_MIN, COR_TEXTO, COR_RESALTADO,
    GROSOR_CONTORNO_TEXTO, COR_CONTORNO_TEXTO, COR_FONDO_TEXTO, PADDING_FONDO_TEXTO,
    COR_LIÑA_SEGUINTE, ALPHA_LIÑA_SEGUINTE, FACTOR_FONTE_LIÑA_SEGUINTE, ESPACIADO_LIÑAS,
    MOSTRAR_LIÑA_SEGUINTE, MODO_SILABICO
)
from text_processing import dic_pyphen


# Renderiza a imaxe la linea principal de texto. VARIAS MELLORAS:
#Silabeador implementado --> chequear mais abaixo a info
#
def render_line_image(line_info: dict, t_offset: float, clip_width: int = TEXT_CLIP_WIDTH, 
                      font_path: str = FONTE, font_size: int = TAMAÑO_FONTE, 
                      normal_color: str = COR_TEXTO, highlight_color: str = COR_RESALTADO) -> np.ndarray:


    texto_completo = line_info["line_text"]
    
    #Aqui temos que usar fuentes fijas para as lineas pero o problema é que si a frase é moi larga(xa que a delimita o salto de linea),
    #pois temos que reducir o tamaño nese caso (improbable, a maioria de casos son frases cortas)
    tamaño_fonte_dinamico = font_size
    if len(texto_completo) > 100:  
        factor_reduccion = min(1.0, 100 / len(texto_completo))
        tamaño_fonte_dinamico = max(TAMAÑO_FONTE_MIN, int(font_size * factor_reduccion))
    
    
    try:
        fonte = ImageFont.truetype(font_path, tamaño_fonte_dinamico)
    except Exception as e:
        print(f"Non se puido cargar a fonte {e}")        
        fonte = ImageFont.load_default()
    
    #axustes visuales varios:
    lineasAjustadas = []
    palabras = texto_completo.split()
    lineaActual = ""
    
    ancho_maximo = clip_width - 2 * PADDING_FONDO_TEXTO    
    for palabra in palabras:
        if not lineaActual:
            lineaActual = palabra
            continue
            
        liñaPrueba = lineaActual + " " + palabra
        ancho_texto = fonte.getlength(liñaPrueba) if hasattr(fonte, 'getlength') else fonte.getsize(liñaPrueba)[0]
        
        if ancho_texto <= ancho_maximo:
            lineaActual = liñaPrueba
        else:
            lineasAjustadas.append(lineaActual)
            lineaActual = palabra
    
    if lineaActual:
        lineasAjustadas.append(lineaActual)
    
    if not lineasAjustadas:
        lineasAjustadas = [texto_completo]
    
    altura_liña = int(tamaño_fonte_dinamico * 1.4)  #puxen un espaciado de linea un 40% mais alto ca o tamaño da fonte

    #aqui temos q calcular a altura total para todas as lineas visuales e asegurar unha altura minima (para as lineas cortas tamen. REVISAR)
    altura_minima = tamaño_fonte_dinamico + 2 * PADDING_FONDO_TEXTO
    altura_total = max(altura_minima, len(lineasAjustadas) * altura_liña + 2 * PADDING_FONDO_TEXTO)  


    #tuven que poñer esto para asegurar a consistencia no posicionamento.
    imaxe = Image.new("RGBA", (clip_width, altura_total), (0, 0, 0, 0))
    debuxar = ImageDraw.Draw(imaxe)
    
    capa_fondo = Image.new("RGBA", (clip_width, altura_total), (0, 0, 0, 0)) #fondo +- transparente
    debuxar_fondo = ImageDraw.Draw(capa_fondo)
    
    
    ancho_maximo_liña = 0
    for liña in lineasAjustadas:
        ancho_liña = fonte.getlength(liña) if hasattr(fonte, 'getlength') else fonte.getsize(liña)[0]  #serviume esto para o problema do ancho. REVISAR A REFERENCIA EN INTERNET PARA AÑADILA NA MEMORIA!!!
        ancho_maximo_liña = max(ancho_maximo_liña, ancho_liña)     
    

    #Fondo trnsparente con bordes redondeados
    ancho_minimo = int(clip_width * 0.4)  #colle polo menos un 40% do ancho disponible do clip
    ancho_fondo = max(ancho_minimo, min(ancho_maximo_liña + 2 * PADDING_FONDO_TEXTO, clip_width))
    x_fondo = (clip_width - ancho_fondo) // 2
    

    #o fondo vai ser un rectangulo. Verifico ahi si a version do PIL soporta a funcion de rounded_rectangle porque me daba problemas
    if hasattr(debuxar_fondo, 'rounded_rectangle'):
        debuxar_fondo.rounded_rectangle(
            [(x_fondo, 0), (x_fondo + ancho_fondo, altura_total)],
            radius=10,  # Radio de las esquinas redondeadas
            fill=COR_FONDO_TEXTO
        )
    else:
        
        #polo problema ese fago un fallback para versions antiguas de PIL
        debuxar_fondo.rectangle(
            [(x_fondo, 0), (x_fondo + ancho_fondo, altura_total)],
            fill=COR_FONDO_TEXTO
        )    

    # Vale, IMPORTANTE, arreglei o silabeador, xa non fai cousas raras cos caracteres especiales. Esta documentado nas notas
    #COMO FUNCIONA? --> primeiro calculo o progreso temporal basandome nos segmentos de audio (usase tanto o nº de segmentos como o progreso dentro do segmento actual)
    # Promediamos o progreso temporal e o progreso de segmentos. Crease a estructura de silabas do texto orixinal
    # e faise un calculo de cantas silabas resaltar en base ao progreso combinado e renderizase línea por línea e sílaba por sílaba

    if MODO_SILABICO and line_info.get("words"):

        tempoActual = line_info["start"] + t_offset
        tempoActual = line_info["start"] + t_offset
        duracion_total_liña = line_info["end"] - line_info["start"]
        
        if duracion_total_liña > 0:
            progreso_temporal = min(1.0, max(0.0, t_offset / duracion_total_liña))
            
            segmentos_pasados = 0
            bonus_progreso_segmento = 0.0
            
            for i, seg in enumerate(line_info["words"]):
                if tempoActual >= seg["end"]:
                    segmentos_pasados += 1
                elif tempoActual >= seg["start"]:

                    #Estamos dentro deste segmento
                    duracion_seg = seg["end"] - seg["start"]
                    if duracion_seg > 0:
                        progreso_seg = (tempoActual - seg["start"]) / duracion_seg
                        bonus_progreso_segmento = progreso_seg / len(line_info["words"])
                    break
            
            progreso_segmento = (segmentos_pasados / len(line_info["words"])) if line_info["words"] else 0.0
            progreso_final = min(1.0, progreso_segmento + bonus_progreso_segmento)
            
            progreso_combinado = (progreso_temporal * 0.3) + (progreso_final * 0.7) 
        else:
            progreso_combinado = 0.0
        
        info_todas_silabas = []  # Lista de [silaba, es_final_de_palabra]
        
        for palabra in texto_completo.split():

            silabas_palabra = dic_pyphen.inserted(palabra).split('-')
            
            if len(silabas_palabra) <= 1:   # Palabra non divisible
                
                info_todas_silabas.append((palabra, True))
            else:
                # si que é divisible
                for i, sil in enumerate(silabas_palabra):
                    e_ultima_silaba = (i == len(silabas_palabra) - 1)
                    info_todas_silabas.append((sil, e_ultima_silaba))
        
        # Calculalse cantas silabas resaltar dependendo do progreso
        total_silabas = len(info_todas_silabas)
        silabas_para_resaltar = int(progreso_combinado * total_silabas)
        
        
        indice_silaba = 0
        
        for i, liña in enumerate(lineasAjustadas):
            y = i * altura_liña + PADDING_FONDO_TEXTO
            
            ancho_liña = fonte.getlength(liña) if hasattr(fonte, 'getlength') else fonte.getsize(liña)[0]    #fajo un cálculo do ancho total da linea para o tema de que este centrada
            x = (clip_width - ancho_liña) // 2
            
            palabras_liña = liña.split()
            
            for idx_palabra, palabra in enumerate(palabras_liña):
                silabas_palabra = dic_pyphen.inserted(palabra).split('-')
                
                if len(silabas_palabra) <= 1:
                    # se a palabra é non divisible -> renderizar completa
                    cor = highlight_color if indice_silaba < silabas_para_resaltar else normal_color
                    debuxar.text((x, y), palabra, font=fonte, fill=cor,
                             stroke_width=GROSOR_CONTORNO_TEXTO, stroke_fill=COR_CONTORNO_TEXTO)
                    ancho_palabra = fonte.getlength(palabra) if hasattr(fonte, 'getlength') else fonte.getsize(palabra)[0]
                    x += ancho_palabra
                    indice_silaba += 1
                else:
                    # se é divisible -> renderizase silaba por silaba
                    for idx_sil, sil in enumerate(silabas_palabra):
                        cor = highlight_color if indice_silaba < silabas_para_resaltar else normal_color
                        debuxar.text((x, y), sil, font=fonte, fill=cor,
                                 stroke_width=GROSOR_CONTORNO_TEXTO, stroke_fill=COR_CONTORNO_TEXTO)
                        ancho_sil = fonte.getlength(sil) if hasattr(fonte, 'getlength') else fonte.getsize(sil)[0]
                        x += ancho_sil
                        indice_silaba += 1
                
                # IMPORTANTE: Añadir espacio pois de cada palabra (menos a ultima da linea) REVISAR ESTO -> contraproducente? Non se ve demasiado smooth
                if idx_palabra < len(palabras_liña) - 1:
                    ancho_espacio = fonte.getlength(" ") if hasattr(fonte, 'getlength') else fonte.getsize(" ")[0]
                    x += ancho_espacio    
    else:
        #original antes do silabeador: Esto seria para o modo de resaltado palabra por palabra por si acaso, q é como fai whisperx, fai un srt a nivel de palabra, non de silaba nin frase (visualmente incomodo para o resaltado)
        palabras = texto_completo.split()
        palabras_para_resaltar = 0
        
        # para sincronizar usanse os tempos dos segmentos de palabras
        if line_info.get("words"):
            for i, seg in enumerate(line_info["words"]):
                tempo_relativo_palabra = seg["start"] - line_info["start"]
                if t_offset >= tempo_relativo_palabra:
                    palabras_para_resaltar = i + 1
        else:
            #outro fallback q avanza proporcional ao tempo
            ratio_progreso = min(1.0, max(0.0, t_offset / (line_info["end"] - line_info["start"])))
            palabras_para_resaltar = int(ratio_progreso * len(palabras))
        
        #Vanse dibujando as lineas e as palabras
        palabras_asignadas = 0
        for i, liña in enumerate(lineasAjustadas):
            palabras_liña = liña.split()
            y = i * altura_liña + PADDING_FONDO_TEXTO
            
            ancho_liña = fonte.getlength(liña) if hasattr(fonte, 'getlength') else fonte.getsize(liña)[0]   
            x = (clip_width - ancho_liña) // 2
            
            for palabra in palabras_liña:
                cor = highlight_color if palabras_asignadas < palabras_para_resaltar else normal_color
                
                debuxar.text((x, y), palabra, font=fonte, fill=cor,
                         stroke_width=GROSOR_CONTORNO_TEXTO, stroke_fill=COR_CONTORNO_TEXTO)
                
                #Avanzase a posivion x para a siguiente palabra
                ancho_palabra = fonte.getlength(palabra) if hasattr(fonte, 'getlength') else fonte.getsize(palabra)[0]
                x += ancho_palabra + (fonte.getlength(" ") if hasattr(fonte, 'getlength') else fonte.getsize(" ")[0])
                
                palabras_asignadas += 1
    
    imaxe = Image.alpha_composite(capa_fondo, imaxe)
    
    frame = np.array(imaxe.convert("RGB"))
    return frame


#Funcion de dibujado da linea siguiente (ALTERNATIVA seria que aparecesa a linea actual un pouco antes de que empece o cantante)
# feito para que se vexa un pouco mais transparente e mais pequena
def render_next_line_image(line_info: dict, clip_width: int = TEXT_CLIP_WIDTH,
                        font_path: str = FONTE, font_size: int = None) -> np.ndarray:

    if font_size is None:

        font_size = int(TAMAÑO_FONTE * FACTOR_FONTE_LIÑA_SEGUINTE)
        
    texto_completo = line_info["line_text"]
    
    # tamaño fijo a non ser que sea unha frase moi larga
    tamaño_fonte_dinamico = font_size
    if len(texto_completo) > 100:
        factor_reduccion = min(1.0, 100 / len(texto_completo))
        tamaño_fonte_dinamico = max(TAMAÑO_FONTE_MIN * FACTOR_FONTE_LIÑA_SEGUINTE, int(font_size * factor_reduccion))
    
    try:
        fonte = ImageFont.truetype(font_path, tamaño_fonte_dinamico)
    except Exception as e:
        print(f"fallo cargando a fonte {e}")
        fonte = ImageFont.load_default()
    
    lineasAjustadas = []
    palabras = texto_completo.split()
    lineaActual = ""
    
    ancho_maximo = clip_width - 2 * PADDING_FONDO_TEXTO
    
    for palabra in palabras:
        if not lineaActual:
            lineaActual = palabra
            continue
            
        liñaPrueba = lineaActual + " " + palabra
        ancho_texto = fonte.getlength(liñaPrueba) if hasattr(fonte, 'getlength') else fonte.getsize(liñaPrueba)[0]
        
        if ancho_texto <= ancho_maximo:
            lineaActual = liñaPrueba
        else:
            lineasAjustadas.append(lineaActual)
            lineaActual = palabra
    
    if lineaActual:
        lineasAjustadas.append(lineaActual)
    
    if not lineasAjustadas:
        lineasAjustadas = [texto_completo]
    
    altura_liña = tamaño_fonte_dinamico + 10
    altura_total = len(lineasAjustadas) * altura_liña + 2 * PADDING_FONDO_TEXTO    
    imaxe = Image.new("RGBA", (clip_width, altura_total), (0, 0, 0, 0))
    debuxar = ImageDraw.Draw(imaxe)
    capa_fondo = Image.new("RGBA", (clip_width, altura_total), (0, 0, 0, 0))    
    debuxar_fondo = ImageDraw.Draw(capa_fondo)
    
    ancho_maximo_liña = 0
    for liña in lineasAjustadas:
        ancho_liña = fonte.getlength(liña) if hasattr(fonte, 'getlength') else fonte.getsize(liña)[0]
        ancho_maximo_liña = max(ancho_maximo_liña, ancho_liña)
    
    colorDeFondoDaSiguienteLinea = (COR_FONDO_TEXTO[0], COR_FONDO_TEXTO[1], COR_FONDO_TEXTO[2], 
                         int(COR_FONDO_TEXTO[3] * ALPHA_LIÑA_SEGUINTE))
    ancho_fondo = min(ancho_maximo_liña + 2 * PADDING_FONDO_TEXTO, clip_width)
    x_fondo = (clip_width - ancho_fondo) // 2
    debuxar_fondo.rectangle(
        [(x_fondo, 0), (x_fondo + ancho_fondo, altura_total)],
        fill=colorDeFondoDaSiguienteLinea
    )
    
    for i, liña in enumerate(lineasAjustadas):
        y = i * altura_liña + PADDING_FONDO_TEXTO
        
        ancho_liña = fonte.getlength(liña) if hasattr(fonte, 'getlength') else fonte.getsize(liña)[0]
        x = (clip_width - ancho_liña) // 2
        
        debuxar.text((x, y), liña, font=fonte, fill=COR_LIÑA_SEGUINTE,
                 stroke_width=int(GROSOR_CONTORNO_TEXTO * 0.75), stroke_fill=COR_CONTORNO_TEXTO)
    
    imaxe = Image.alpha_composite(capa_fondo, imaxe)
    
    frame = np.array(imaxe.convert("RGB"))
    return frame


# Función para crear o clip de video para a linea de karaoke. Como funciona?
# iniciase advance segundos antes do tempo real (non negativo) e dura hasta (line_info["end"] - line_info["start"] + advance + duration_padding)
# ten o wrap automatico polo tema dos textos largos
# renderizase a imagen da línea con t - display_offset (se xa é positivo)
# Se a configuración permite mostrar a línea siguiente e temos a información, combinamos os dous frames e crease un frame combinado con espacio abondo entre lineas. 
# Centro horizontalmente as duas imagenes, copio la linea actual na parte de arriba e a linea siguiente ponse na parte de abaixo
# CHEQUEAR A REF EN INTERNET, esta explicado mais ou menos
def create_karaoke_text_clip(line_info: dict, next_line_info: dict = None, advance: float=0.5, duration_padding: float=0.5):

    duracion_liña = line_info["end"] - line_info["start"]
    duracion_clip = duracion_liña + advance + duration_padding
    offset_visualizacion = advance  # esto é o retraso interno do clip

    def facer_frame(t):
        # t es el tiempo transcurrido en el clip
        
        t_efectivo = max(t - offset_visualizacion, 0) #t seria o tempo transcurrido no clip
        
        frameActual = render_line_image(line_info, t_efectivo)
        
        
        if MOSTRAR_LIÑA_SEGUINTE and next_line_info:
            frame_seguinte = render_next_line_image(next_line_info)
            
            
            altura1 = frameActual.shape[0]
            altura2 = frame_seguinte.shape[0]
            ancho = max(frameActual.shape[1], frame_seguinte.shape[1])
            
            altura_combinada = altura1 + ESPACIADO_LIÑAS + altura2
            frame_combinado = np.zeros((altura_combinada, ancho, 3), dtype=np.uint8)
            
            
            offset_x1 = (ancho - frameActual.shape[1]) // 2
            offset_x2 = (ancho - frame_seguinte.shape[1]) // 2
            
            frame_combinado[:altura1, offset_x1:offset_x1+frameActual.shape[1]] = frameActual
            
            y_seguinte_liña = altura1 + ESPACIADO_LIÑAS
            frame_combinado[y_seguinte_liña:y_seguinte_liña+altura2, offset_x2:offset_x2+frame_seguinte.shape[1]] = frame_seguinte
            
            return frame_combinado
        
        # se non hai linea siguiente solo se devolve o frame actual
        return frameActual

    clip_texto = VideoClip(facer_frame, duration=duracion_clip)
    return clip_texto
