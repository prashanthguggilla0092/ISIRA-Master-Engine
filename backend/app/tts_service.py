from google.cloud import texttospeech


client = texttospeech.TextToSpeechClient()


DEFAULT_VOICES = {
    "te-IN": "te-IN-Chirp3-HD-Achernar",
    "hi-IN": "hi-IN-Chirp3-HD-Achernar",
    "en-IN": "en-IN-Chirp3-HD-Achernar",
    "ta-IN": "ta-IN-Chirp3-HD-Achernar",
    "kn-IN": "kn-IN-Chirp3-HD-Achernar",
    "ml-IN": "ml-IN-Chirp3-HD-Achernar",
    "mr-IN": "mr-IN-Chirp3-HD-Achernar",
    "bn-IN": "bn-IN-Chirp3-HD-Achernar",
    "gu-IN": "gu-IN-Chirp3-HD-Achernar",
    "pa-IN": "pa-IN-Chirp3-HD-Achernar",
    "ur-IN": "ur-IN-Chirp3-HD-Achernar",
}


def _get_voice(language_code: str) -> str:
    return DEFAULT_VOICES.get(
        language_code,
        "en-IN-Chirp3-HD-Achernar",
    )


def synthesize_speech(
    text: str,
    language_code: str = "te-IN",
) -> bytes:
    input_text = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=_get_voice(language_code),
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
    )

    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config,
    )

    return response.audio_content
