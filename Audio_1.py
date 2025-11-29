import ffmpeg
import speech_recognition as sr
from io import BytesIO

def transcribe_audio_file(webm_bytes: bytes, language="en-US") -> str:
    # Build ffmpeg pipeline
    stream = (
        ffmpeg
        .input("pipe:", format="webm")     # read WebM from stdin
        .output("pipe:", format="wav", ac=1, ar=16000)
    )
    # Run ffmpeg and capture WAV output
    out, err = stream.run(
        capture_stdout=True,
        capture_stderr=True,
        input=webm_bytes
    )

    wav_io = BytesIO(out)
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_io) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio_data = recognizer.record(source)

    return recognizer.recognize_google(audio_data, language=language)
