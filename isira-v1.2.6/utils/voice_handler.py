# ISIRA Voice Synthesis Module
try:
    from google.cloud import texttospeech
except ImportError:
    pass

def speak(text: str, filename: str):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="te-IN", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open(f"voice_assets/{filename}.mp3", "wb") as out:
        out.write(response.audio_content)
    print(f"Voice Output Saved: voice_assets/{filename}.mp3")
