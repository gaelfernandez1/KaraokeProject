# Karaoke con IA - Proxecto TFG - Gael Fernández

Creación automática de vídeos de karaoke multilinüe mediante ferramentas de aprendizaxe profundo utilizando demucs, whisperx e moviepy.


## Guía de instalación

Paso 1: Descargar Docker Desktop no equipo

Paso 2: Instalar ImageMagick no equipo e metelo nesta ruta: "C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe" si estás en Windows, si estás en linux "/usr/bin/convert"
Ou se non ir ao archivo config.py e cambiar a ruta ahí
Nesta páxina está exlpicado: https://dev.to/muddylemon/making-my-own-karaoke-videos-with-ai-4b8l
        
Paso 3: Instalar ffmpeg no equipo. a version usada no proxecto é esta: ffmpeg-2025-01-20-git-504df09c34-full_build

Paso 4: Istalar anaconda e usar o anaconda prompt. a versión de python usada é a 3.10.16. Opcional usar un conda environment

Paso 5: Clonar o repositorio do proxecto


## Instrucións de uso

### Compilar e executar os contedores

Primeiro abre Docker Desktop e deixa a máquina correndo (Engine Running), con abrir Docker Desktop é suficiente en principio.

Agora no anaconda prompt, meterse na carpeta do proxecto e executar os seguintes comandos:

```bash
docker-compose build
docker-compose up -d
```

Despois de iniciar os contedores, accede á aplicación web en: http://127.0.0.1:5000/


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

### Limpar datos

```bash
docker exec -it demucs_container bash -c "rm -rf /data/*"
```

