# test_demucs.py
import subprocess

audio_input = "data/test_audio.mp3"

# Llamamos al comando demucs mediante subprocess
# Podrías usar la API de Python de Demucs, pero
# el CLI a veces es más sencillo para empezar.
command = ["demucs", audio_input]
subprocess.run(command)
