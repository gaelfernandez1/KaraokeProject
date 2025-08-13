# Karaoke con IA - Proxecto TFG - Gael Fernández

Creación automática de vídeos de karaoke multilinüe mediante ferramentas de aprendizaxe profundo utilizando demucs, whisperx e moviepy.


## Guía de instalación

Paso 1: Descargar Docker Desktop no equipo

Paso 2: Istalar anaconda e usar o anaconda prompt(ou o sistema preferido de cada usuario). a versión de python usada é a 3.10.16 pero probablemente funciona con versións de python superiores. Opcional usar un conda environment

Paso 3: Clonar o repositorio do proxecto


## Instrucións de uso

### Compilar e executar os contedores

Primeiro abre Docker Desktop e deixa a máquina correndo (Engine Running), con abrir Docker Desktop é suficiente en principio.

Agora no anaconda prompt, meterse na carpeta do proxecto e executar os seguintes comandos:

```bash
docker-compose build
docker-compose up -d
```

Despois de iniciar os contedores, accede á aplicación web en: http://127.0.0.1:5000/  en local.

Para compartir a web con terceiros, vai a http://localhost:4040    (ngrok),  copia a nova URL pública e compártea!

## Activación de Speaker Diarization
1. Marcar checkbox "Enable Speaker Diarization" na interfaz web
2. Introducir token válido de HuggingFace. IMPORTANTE: Tras autenticarte, hai que aceptar os termos e condicións dos seguintes modelos:
https://huggingface.co/pyannote/speaker-diarization-3.1
https://huggingface.co/pyannote/segmentation-3.0

Despois crea un token modo READ na seguinte ligazón:
https://huggingface.co/settings/tokens

3. Procesar video normalmente


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
```

### Copiar cousas do contenedor a local
docker cp whisperx_container:/data/. "ruta a onde queiras copiar"    
docker cp demucs_container:/KaraokeProject/output/. "ruta a onde queiras copiar"

docker cp whisperx_container:/data/. "C:\Users\gaelb\Desktop\KaraokeProject\carpetaconsrt" 

### Limpar datos

```bash
docker exec -it demucs_container bash -c "rm -rf /data/*"
```

### Liberar espazo de contedores no pc(docker)

```bash
docker system prune -a --volumes
```
