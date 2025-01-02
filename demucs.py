import subprocess

# Ruta al archivo de audio que deseas procesar
ruta_audio = "prueba.mp3"

# Comando para ejecutar Demucs
comando = ["demucs", "-d", "cpu", ruta_audio]

# Ejecutar el comando
subprocess.run(comando)
