from module.utils import config, timing_decorator
import azure.cognitiveservices.speech as speechsdk
import asyncio
import time


class SpeechSynthesizerWrapper:
    def __init__(self, config: speechsdk.SpeechConfig):
        """Initialize the Speech Synthesizer and keep the connection open."""
        self.config = config
        self.synthesizer = speechsdk.SpeechSynthesizer(config, None)
        self.connection = speechsdk.Connection.from_speech_synthesizer(self.synthesizer)
        self.connection.open(True)  # Keeps the connection open
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ Connection opened and ready for synthesis."
        )

        self.last_request_time = time.time()  # Track last synthesis request
        self.auto_close_task = None  # Async task for closing

    def start_auto_close_timer(self):
        """Start an async task to check inactivity every 30 seconds and close if idle for 2 minutes."""
        if self.auto_close_task:
            self.auto_close_task.cancel()  # Cancel any previous task

        async def auto_close():
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds
                time_since_last_request = time.time() - self.last_request_time

                if time_since_last_request >= 120:  # No requests in last 2 min
                    print(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⏳ No activity for 2 minutes. Closing connection."
                    )
                    self.close_connection()
                    break  # Stop loop once connection is closed
                else:
                    print(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Auto-close skipped. Last request was {time_since_last_request:.1f} seconds ago."
                    )

        self.auto_close_task = asyncio.create_task(auto_close())
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⏳ Auto-close timer started (2 min, checks every 30s)."
        )

    async def synthesize(self, text):
        """Synthesize speech from text while keeping the connection alive."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🎙️ Synthesizing text: {text}")
        self.last_request_time = time.time()  # Update request time

        try:
            # result = await self.synthesizer.speak_text_async(text).get()
            result = await asyncio.to_thread(
                self.synthesizer.speak_text_async(text).get
            )
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ Speech synthesis completed successfully."
                )
                self.start_auto_close_timer()  # Restart the auto-close timer after successful request
                return result.audio_data
            elif result.reason == speechsdk.ResultReason.Canceled:
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Speech synthesis canceled: {result.cancellation_details.reason}"
                )
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error: {e}")
            return None

    def close_connection(self):
        """Close the connection explicitly and stop the auto-close task."""
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🚪 Closing connection due to inactivity."
        )
        self.connection.close()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Connection closed.")
        self.auto_close_task = None  # Reset task
