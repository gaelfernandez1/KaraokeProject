# Karaoke con IA - Proxecto TFG - Gael Fernández

Creación automática de vídeos de karaoke multilinües mediante ferramentas de aprendizaxe profundo utilizando Demucs, WhisperX e MoviePy.


## Guía de instalación

Paso 1: Descargar Docker Desktop no equipo

Paso 2: Instalar anaconda e usar o anaconda prompt(ou o sistema preferido de cada usuario). a versión de python usada é a 3.10.16 pero pode funcionar con versións de python superiores. Opcional usar un conda environment

Paso 3: Clonar o repositorio do proxecto


## Instrucións de uso

### Compilar e executar os contedores

Primeiro abre Docker Desktop e deixa a máquina correndo (Engine Running), con abrir Docker Desktop é suficiente.

Agora no anaconda prompt, meterse na carpeta do proxecto e executar os seguintes comandos:

```bash
docker-compose build
docker-compose up -d
```

Despois de iniciar os contedores, accede á aplicación web en: http://127.0.0.1:5000/  en local.

Para compartir a web con terceiros, vai a http://localhost:4040    (ngrok),  copia a nova URL pública e compártea!

## Activación de Speaker Diarization
1. Marcar checkbox "Enable Speaker Diarization" na interface web

2. Introducir token válido de HuggingFace. IMPORTANTE: Tras autenticarse, hai que aceptar os termos e condicións dos seguintes modelos: https://huggingface.co/pyannote/speaker-diarization-3.1 e https://huggingface.co/pyannote/segmentation-3.0

3. Despois crea un token modo READ na seguinte ligazón: https://huggingface.co/settings/tokens

4. Procesar vídeo normalmente


## Comandos para debug

### Entrar nos contedores

```bash
docker exec -it demucs_container /bin/bash
docker exec -it whisperx_container /bin/bash
```

### Ver rexistros de erros

```bash
docker-compose logs -f demucs
docker-compose logs -f whisperx
docker-compose logs -f celery_worker
```

### Copiar cousas do contenedor a local
docker cp whisperx_container:/data/. "ruta a onde queiras copiar"    
docker cp demucs_container:/KaraokeProject/output/. "ruta a onde queiras copiar"
<!--  docker cp whisperx_container:/data/. "C:\Users\gaelb\Desktop\KaraokeProject\carpetaconsrt"  -->


### Limpar datos

```bash
docker exec -it demucs_container bash -c "rm -rf /data/*"
```

### Liberar espazo de contedores no pc (Docker)

```bash
docker system prune -a --volumes
```

## Recomendacións

Para o modo manual (aliñación forzada), os modelos grandes non sempre dan mellores resultados. Recoméndase:
  - small ou medium son ideales para alineación forzada, a non ser que se conte con grandes capacidades de GPU.
  - large-v2 ou v3 só para transcrición automática cando se precise máxima precisión.
