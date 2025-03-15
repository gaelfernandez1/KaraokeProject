Compilar y ejecutar contenedores

docker-compose build
docker-compose up -d

Entrar al contenedor:

docker exec -it demucs_container /bin/bash
docker exec -it whisperx_container /bin/bash

Para ver errores:

docker-compose logs -f demucs
docker-compose logs -f whisperx

docker exec -it demucs_container bash -c "rm -rf /data/*"