import glob
import os
import subprocess
import torch
import whisper

def separar_pistas(audio_path, output_dir="./demucs_output"):
    """
    Usa Demucs para separar las pistas de una canción y retorna la pista vocal (vocals.wav).
    """
    os.makedirs(output_dir, exist_ok=True)
    print("Separando pistas con Demucs...")

    # Ejecuta Demucs
    subprocess.run(["demucs", "-o", output_dir, audio_path], check=True)
    
    # Busca la subcarpeta generada por Demucs
    vocals_path_pattern = os.path.join(output_dir, "htdemucs", "*", "vocals.wav")
    vocals_files = glob.glob(vocals_path_pattern)
    
    if not vocals_files:
        raise FileNotFoundError(f"No se encontró ningún archivo vocal en {vocals_path_pattern}")
    
    # Usa el primer archivo encontrado
    vocals_wav = vocals_files[0]
    print(f"Pista vocal (WAV) generada en: {vocals_wav}")
    return vocals_wav

def transcribir_audio(audio_path, model_type="base"):
    """
    Usa Whisper para transcribir la pista vocal.
    """
    print("Transcribiendo audio con Whisper...")

    # Verifica si CUDA (GPU) está disponible
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Carga el modelo con el dispositivo adecuado
    model = whisper.load_model(model_type, device=device)
    result = model.transcribe(audio_path)
    return result["text"]

def main():
    # Ruta al archivo de entrada
    input_audio = "prueba.mp3"  # Ajusta aquí el nombre real de tu archivo
    
    # Paso 1: Separar pistas con Demucs
    vocals_wav = separar_pistas(input_audio)
    
    # Paso 2: Transcribir la pista vocal (WAV) con Whisper
    letra = transcribir_audio(vocals_wav)
    print("\n=========== LETRA TRANSCRITA ===========")
    print(letra)

if __name__ == "__main__":
    main()
