
import azure.cognitiveservices.speech as speechsdk
import os

audio_path = os.path.join(os.getcwd(), "audios")
if not os.path.exists(audio_path):
    os.mkdir(audio_path)

key = "69c5af99c15547eaa10f4fef81c17317"
region = "eastus"

class HCMSpeechOut:

    def __init__(self) -> None:
        self.speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        self.speech_config.speech_recognition_language="en-US"
        
        
        # self.audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True) # NOTE: you can use audio in a vm.
        # self.audio_config = speechsdk.audio.AudioOutputConfig(filename="audio.txt")
        # self.out_audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        # self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=self.audio_config)

    def recognize_from_microphone(self):
        self.audio_config = speechsdk.audio.AudioOutputConfig(filename="audio.txt")
        self.out_audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=self.audio_config)

        print("Speak into your microphone.")
        speech_recognition_result = self.speech_recognizer.recognize_once_async().get()
        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print("Recognized: {}".format(speech_recognition_result.text))
            return speech_recognition_result.text
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
            return "ERROR"
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                # print("Did you set the speech resource key and region values?")
                return "ERROR"
            return "ERROR"

    async def recognize_from_filepath(self, audio_path: str):

        audio_input = speechsdk.audio.AudioConfig(filename=audio_path)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_input)
        speech_recognition_result = speech_recognizer.recognize_once_async().get()

        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
            # print("Recognized: {}".format(speech_recognition_result.text))
            return speech_recognition_result.text
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
            return "ERROR"
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
            return "ERROR"
        
    def recognize_from_audio_stream(self, audio_stream):
        # self.stream_audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
        # recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=self.stream_audio_config)

        push_stream = speechsdk.audio.PushAudioInputStream(stream_format=speechsdk.audio.AudioStreamFormat())
        
        push_stream.write(audio_stream.read())
        audio_stream.seek(0)
        push_stream.close()
        audio_stream.truncate(0)

        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_config)

        result = recognizer.recognize_once()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        else:
            return "ERROR"
    
    def synthesize_to_audio_stream(self, text):
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=None)
        result = synthesizer.speak_text_async(text).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return result.audio_data
        else:
            return None

    def synthesize_english(self, text):
    
        self.speech_config.speech_synthesis_voice_name= "en-US-EmmaNeural"
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=self.out_audio_config)

        speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()
        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("Speech synthesized for text [{}]".format(text))
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            print("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    print("Error details: {}".format(cancellation_details.error_details))
                    print("Did you set the speech resource key and region values?")


    async def synthesize_english_to_filepath(self, text, response_id):
        self.speech_config.speech_synthesis_voice_name = "en-US-EmmaNeural"
        audio_response_path = os.path.join(audio_path, f"response_audio_{response_id}.wav")

        audio_config = speechsdk.audio.AudioOutputConfig(filename=audio_response_path)
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_config)
        speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

        if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # print("Speech synthesized for text [{}]".format(text))
            # with open(audio_response_path, "wb") as audio_file:
            #     audio_file.write(speech_synthesis_result.audio_data)
            return audio_response_path
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            print("Speech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    print("Error details: {}".format(cancellation_details.error_details))
                    print("Did you set the speech resource key and region values?")
            return None



if __name__ == "__main__":

    import base64
    import io

    def audio_to_base64(file_path):
        with open(file_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        return audio_base64

    audio_file_path = '/home/alijoe/Downloads/record.wav'  # Replace with your audio file path
    base64_audio = audio_to_base64(audio_file_path)
    audio_data = base64.b64decode(base64_audio)
    audio_stream = io.BytesIO(audio_data)
    
    hcm_speech = HCMSpeechOut()
    # print (hcm_speech.recognize_from_audio_stream(audio_stream))
    print (hcm_speech.recognize_from_filepath(audio_file_path))
    # while True:
    #     text = hcm_speech.recognize_from_microphone()
    #     hcm_speech.synthesize_english(text)
    #     print ("Done")
    #     time.sleep(3)


