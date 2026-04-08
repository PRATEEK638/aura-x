import threading
import queue
import time
from typing import Callable, Optional
from core.logger import setup_logger

logger = setup_logger("aura_x.voice.listener")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("speech_recognition not available. Voice input disabled.")


class VoiceListener:
    def __init__(self, wake_word: str, on_command: Callable[[str], None]):
        self.wake_word = wake_word.lower()
        self.on_command = on_command
        self.running = False
        self._stop_event = threading.Event()
        self._audio_queue: queue.Queue = queue.Queue()
        self._active = SR_AVAILABLE

        if SR_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            self.recognizer.phrase_threshold = 0.3
            self.recognizer.non_speaking_duration = 0.5
            try:
                self.microphone = sr.Microphone()
                self._calibrate()
            except Exception as e:
                logger.error(f"Microphone init error: {e}")
                self._active = False
        else:
            self._active = False

    def _calibrate(self):
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Microphone calibrated for ambient noise")
        except Exception as e:
            logger.warning(f"Microphone calibration failed: {e}")

    def start_listening(self):
        if not self._active:
            logger.info("Voice listener inactive (no mic or speech_recognition available)")
            return

        self.running = True
        self._stop_event.clear()
        logger.info(f"Voice listener started. Wake word: '{self.wake_word}'")

        proc_thread = threading.Thread(
            target=self._process_audio_queue,
            daemon=True,
            name="AudioProcessor"
        )
        proc_thread.start()

        self._continuous_listen()

    def _continuous_listen(self):
        while self.running and not self._stop_event.is_set():
            try:
                with self.microphone as source:
                    try:
                        audio = self.recognizer.listen(
                            source,
                            timeout=5,
                            phrase_time_limit=15
                        )
                        self._audio_queue.put(audio)
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        logger.debug(f"Listen error: {e}")
                        time.sleep(0.5)
            except Exception as e:
                logger.error(f"Microphone access error: {e}")
                time.sleep(2)

    def _process_audio_queue(self):
        while self.running or not self._audio_queue.empty():
            try:
                audio = self._audio_queue.get(timeout=1)
                text = self._transcribe(audio)
                if text:
                    text_lower = text.lower()
                    if self.wake_word in text_lower:
                        idx = text_lower.find(self.wake_word)
                        command = text[idx + len(self.wake_word):].strip()
                        if command:
                            logger.info(f"Wake word detected, command: {command}")
                            self.on_command(command)
                        else:
                            logger.info("Wake word detected, waiting for command...")
                            try:
                                next_audio = self._audio_queue.get(timeout=6)
                                next_text = self._transcribe(next_audio)
                                if next_text:
                                    self.on_command(next_text)
                            except queue.Empty:
                                pass
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Audio processing error: {e}", exc_info=True)

    def _transcribe(self, audio) -> Optional[str]:
        for engine in [self._try_google, self._try_sphinx]:
            try:
                result = engine(audio)
                if result:
                    return result
            except Exception:
                continue
        return None

    def _try_google(self, audio) -> Optional[str]:
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logger.debug(f"Google STT error: {e}")
            return None

    def _try_sphinx(self, audio) -> Optional[str]:
        try:
            return self.recognizer.recognize_sphinx(audio)
        except Exception:
            return None

    def stop(self):
        self.running = False
        self._stop_event.set()
        logger.info("Voice listener stopped")
