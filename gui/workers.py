"""
Aura-X Background Workers — V4
QThread workers for AI processing, system checks, and voice I/O.
Voice output is BLOCKING in the worker thread so orb animations stay synced.
"""

import time
import threading
from PyQt6.QtCore import QThread, pyqtSignal
from core.logger import setup_logger

logger = setup_logger("aura_x.gui.workers")


class AIWorker(QThread):
    """Process user input through AI and speak the response."""
    response_ready = pyqtSignal(str)       # AI text response
    error_occurred = pyqtSignal(str)       # Error message
    model_used = pyqtSignal(str)           # Which model was used
    speaking_started = pyqtSignal()        # Voice output begins
    speaking_finished = pyqtSignal()       # Voice output ends
    finished_processing = pyqtSignal()     # All done

    def __init__(self, assistant, user_text: str, parent=None):
        super().__init__(parent)
        self._assistant = assistant
        self._user_text = user_text
        self._cancelled = False

    def run(self):
        try:
            # Phase 1: Get AI response
            response = self._assistant.process_input(self._user_text)
            if self._cancelled:
                return

            # Emit model info
            try:
                model = self._assistant.ai_router.get_last_model()
                if model:
                    self.model_used.emit(model)
            except Exception:
                pass

            # Emit response text (for logging/display if needed)
            self.response_ready.emit(response)

            # Phase 2: Speak the response (BLOCKING — waits for speech)
            if not self._cancelled and self._assistant.speaker:
                try:
                    self.speaking_started.emit()
                    # Clean for speech
                    speech_text = response[:300] if len(response) > 300 else response
                    speech_text = speech_text.replace("✓", "").replace("✗", "").replace("⚠", "")
                    speech_text = speech_text.replace("─", "").replace("✦", "")
                    speech_text = speech_text.strip()
                    if speech_text:
                        # Use speak_sync to BLOCK until speech finishes
                        self._assistant.speaker.speak_sync(speech_text)
                    self.speaking_finished.emit()
                except Exception as e:
                    logger.debug(f"Voice output error: {e}")
                    self.speaking_finished.emit()

        except Exception as e:
            logger.error(f"AI Worker error: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            self.finished_processing.emit()

    def cancel(self):
        self._cancelled = True


class VoiceSpeakWorker(QThread):
    """Speak a specific text and emit signals when done."""
    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, speaker, text: str, parent=None):
        super().__init__(parent)
        self._speaker = speaker
        self._text = text

    def run(self):
        try:
            self.speaking_started.emit()
            if self._speaker:
                self._speaker.speak_sync(self._text)
            self.speaking_finished.emit()
        except Exception as e:
            logger.error(f"VoiceSpeakWorker error: {e}")
            self.error_occurred.emit(str(e))
            self.speaking_finished.emit()


class SystemCheckWorker(QThread):
    """Run startup health checks in background."""
    status_update = pyqtSignal(str, bool)
    check_complete = pyqtSignal(dict)

    def run(self):
        results = {}

        # Check Ollama
        try:
            import requests
            from core.config import CONFIG
            url = CONFIG.get("ollama_base_url", "http://localhost:11434")
            resp = requests.get(f"{url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                results["ollama"] = {"available": True, "models": models}
                self.status_update.emit("Ollama", True)
            else:
                results["ollama"] = {"available": False}
                self.status_update.emit("Ollama", False)
        except Exception:
            results["ollama"] = {"available": False}
            self.status_update.emit("Ollama", False)

        # Check NVIDIA API
        try:
            from core.config import CONFIG
            key = CONFIG.get("nvidia_api_key", "")
            available = bool(key and len(key) > 10)
            results["nvidia"] = {"available": available}
            self.status_update.emit("NVIDIA API", available)
        except Exception:
            self.status_update.emit("NVIDIA API", False)

        # Check pyautogui (screen control)
        try:
            import pyautogui
            pyautogui.size()
            results["screen"] = {"available": True}
            self.status_update.emit("Screen Control", True)
        except Exception:
            results["screen"] = {"available": False}
            self.status_update.emit("Screen Control", False)

        # Check voice
        try:
            import pyttsx3
            results["voice"] = {"available": True}
            self.status_update.emit("Voice Output", True)
        except Exception:
            results["voice"] = {"available": False}
            self.status_update.emit("Voice Output", False)

        self.check_complete.emit(results)


class VoiceInputWorker(QThread):
    """Listen for voice input using the microphone."""
    text_recognized = pyqtSignal(str)
    listening_started = pyqtSignal()
    listening_stopped = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = False

    def run(self):
        try:
            import speech_recognition as sr
        except ImportError:
            self.error_occurred.emit("SpeechRecognition not installed")
            return

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300  # More sensitive
        recognizer.dynamic_energy_threshold = True

        try:
            with sr.Microphone() as source:
                self.listening_started.emit()
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("Microphone listening...")
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)
                self.listening_stopped.emit()

                if self._stop:
                    return

                # Try Google first, then offline
                try:
                    text = recognizer.recognize_google(audio, language="en-IN")
                except Exception:
                    text = recognizer.recognize_google(audio)

                if text and text.strip():
                    logger.info(f"Recognized: {text}")
                    self.text_recognized.emit(text.strip())
                else:
                    self.error_occurred.emit("Empty speech")

        except sr.WaitTimeoutError:
            self.listening_stopped.emit()
            self.error_occurred.emit("No speech detected — try again")
        except sr.UnknownValueError:
            self.listening_stopped.emit()
            self.error_occurred.emit("Could not understand — try again")
        except Exception as e:
            self.listening_stopped.emit()
            logger.error(f"Voice input error: {e}")
            self.error_occurred.emit(f"Mic error: {str(e)[:50]}")

    def stop(self):
        self._stop = True
