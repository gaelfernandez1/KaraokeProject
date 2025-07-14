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

### Liberar espazo de contedores no pc(docker)

```bash
docker system prune -a --volumes
```
