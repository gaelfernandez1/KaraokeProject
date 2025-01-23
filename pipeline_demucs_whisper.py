import subprocess
import os

def separate_audio_with_demucs(audio_input):
    """
    Llama a Demucs para separar las pistas de la canción dada.
    Retorna la ruta del archivo de voz resultante (vocals.wav).
    """
    # Ejecutamos demucs
    command = ["demucs", audio_input]
    subprocess.run(command, check=True)

    # Demucs crea la carpeta en "separated/htdemucs/<filename_sin_extension>/"
    base_name = os.path.splitext(os.path.basename(audio_input))[0]
    vocals_path = os.path.join("separated", "htdemucs", base_name, "vocals.wav")

    return vocals_path

def transcribe_with_whisper(audio_input, model="small", language=None):
    """
    Llama a Whisper para transcribir el archivo de audio.
    Retorna la ruta del archivo de texto transcrito.
    """
    command = ["whisper", audio_input, "--model", model]
    
    if language:
        command += ["--language", language]
        
    subprocess.run(command, check=True)

    txt_file = os.path.splitext(os.path.basename(audio_input))[0] + ".txt"
    # => "vocals.txt", pero en la carpeta actual, NO en separated/...
    return txt_file


if __name__ == "__main__":
    # 1. Ruta de un audio de prueba
    original_audio = "data/test_audio.mp3"
    
    # 2. Separar las pistas
    vocals_file = separate_audio_with_demucs(original_audio)
    
    # 3. Transcribir la pista vocal
    transcription_file = transcribe_with_whisper(vocals_file, model="small", language=None)
    
    # 4. Leer e imprimir la transcripción
    with open(transcription_file, "r", encoding="utf-8") as f:
        transcript = f.read()
    
    print("TRANSCRIPCIÓN:\n", transcript)
