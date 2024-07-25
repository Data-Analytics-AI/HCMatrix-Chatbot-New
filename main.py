
import uvicorn
# from api.app import app

if __name__ == "__main__":
    uvicorn.run("api.app:app", host="0.0.0.0", port=5000, reload=True)

    self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=self.audio_config)
    file_name = "outputaudio.wav"
    file_config = speechsdk.audio.AudioOutputConfig(filename=file_name)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=file_config)