import subprocess

audio_input = "data/test_audio.mp3"
command = [
    "whisper", 
    audio_input, 
    "--model", "small", 
]

subprocess.run(command)
