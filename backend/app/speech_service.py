from google.cloud import speech
import subprocess
import tempfile
import os


client = speech.SpeechClient()


SUPPORTED_LANGUAGES = {
    "te-IN",
    "hi-IN",
    "en-IN",
    "ta-IN",
    "kn-IN",
    "ml-IN",
    "mr-IN",
    "bn-IN",
    "gu-IN",
    "pa-IN",
    "ur-IN",
}


def _convert_to_wav(audio_bytes: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as input_file:
        input_file.write(audio_bytes)
        input_path = input_file.name

    output_path = input_path + ".wav"

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                output_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        with open(output_path, "rb") as wav_file:
            return wav_file.read()

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

        if os.path.exists(output_path):
            os.remove(output_path)


def transcribe_audio(
    audio_bytes: bytes,
    language_code: str = "te-IN",
) -> str:
    if language_code not in SUPPORTED_LANGUAGES:
        language_code = "te-IN"

    wav_bytes = _convert_to_wav(audio_bytes)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code,
        enable_automatic_punctuation=True,
    )

    audio = speech.RecognitionAudio(
        content=wav_bytes,
    )

    response = client.recognize(
        config=config,
        audio=audio,
    )

    return " ".join(
        result.alternatives[0].transcript
        for result in response.results
        if result.alternatives
    )
