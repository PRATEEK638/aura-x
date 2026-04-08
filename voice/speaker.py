"""
Aura-X Voice Speaker — edge-tts (Microsoft Neural TTS)
Natural-sounding async TTS with queue-based non-blocking playback.
No pyttsx3 fallback — edge-tts only for natural voice quality.
"""

import threading
import queue
import tempfile
import os
import re
import asyncio
from typing import Optional
from core.logger import setup_logger

logger = setup_logger("aura_x.voice.speaker")

# Check for edge-tts
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not installed. Run: pip install edge-tts")

# Check for pygame (audio playback)
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except Exception:
    PYGAME_AVAILABLE = False
    logger.warning("pygame not available. Run: pip install pygame")


# Natural English voice — Guy is deeper, less robotic
VOICE_DEFAULT = "en-US-GuyNeural"


class VoiceSpeaker:
    """
    Non-blocking TTS using edge-tts (neural) with pygame playback.
    Queues utterances so responses never block the main thread.
    """

    def __init__(self, voice: str = VOICE_DEFAULT):
        self.voice = voice
        self._queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._speaking = False

        self._available = EDGE_TTS_AVAILABLE and PYGAME_AVAILABLE

        if self._available:
            logger.info(f"TTS: edge-tts with voice {self.voice}")
            self._thread = threading.Thread(
                target=self._speech_loop, daemon=True, name="SpeechThread"
            )
            self._thread.start()
        else:
            logger.warning("TTS: Not available (need edge-tts + pygame)")

    def _speech_loop(self):
        """Background loop that processes the speech queue."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.5)
                if text is None:
                    break

                self._speaking = True
                try:
                    self._loop.run_until_complete(self._speak_edge(text))
                except Exception as e:
                    logger.debug(f"Speech error: {e}")
                finally:
                    self._speaking = False
                    self._queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Speech loop error: {e}")
                self._speaking = False

    async def _speak_edge(self, text: str):
        """Use edge-tts to generate audio, then play with pygame."""
        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(tmp_fd)

            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(tmp_path)

            if os.path.exists(tmp_path):
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if self._stop_event.is_set():
                        pygame.mixer.music.stop()
                        break
                    await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"edge-tts error: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def speak(self, text: str, priority: bool = False):
        """Queue text for speech output."""
        if not text or not text.strip():
            return
        if not self._available:
            return

        clean = self._clean_for_tts(text)
        if not clean:
            return

        if priority:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except queue.Empty:
                    break
            self._queue.put(clean)
        else:
            if self._queue.qsize() < 3:
                self._queue.put(clean)

    def _clean_for_tts(self, text: str) -> str:
        """Extract ONLY the conversational part for speech. Skip all data/technical output."""
        if not text:
            return ""

        # Remove markdown formatting
        text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
        text = re.sub(r"_{1,2}(.*?)_{1,2}", r"\1", text)
        text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
        text = re.sub(r"#{1,6}\s*", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

        # Remove code blocks and JSON tool blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r'\{[^{}]*"tool"[^{}]*\}', "", text)

        # Remove all emoji/symbols
        text = re.sub(r'[✓✗⊘📺📐🏗🖱📝⚠🚀📁📂📄📎📊📋⬇⚙💻🎬🎵📸🎓🗂🗑⌨👋]', '', text)

        # Split into lines
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if not lines:
            return ""

        # Take ONLY the first conversational line — skip data lines
        spoken_parts = []
        for line in lines:
            if any([
                line.startswith("•"),
                line.startswith("- "),
                line.startswith("  "),
                "C:\\" in line or "C:/" in line,
                line.startswith("Contents of"),
                line.startswith("Open windows"),
                re.match(r"^\d+\s*→", line),
                re.match(r"^[A-Z]:\\", line),
                line.startswith("System:"),
                line.startswith("CPU:"),
                line.startswith("RAM:"),
                line.startswith("Disk"),
                "%" in line and any(c.isdigit() for c in line),
                len(line) > 100,
            ]):
                break
            spoken_parts.append(line)
            if len(spoken_parts) >= 2:
                break

        result = " ".join(spoken_parts).strip()

        # Final cleanup
        result = re.sub(r"\s+", " ", result)
        result = result.rstrip(":")

        # Cap at 150 chars for natural speech length
        if len(result) > 150:
            for sep in [". ", "! ", "? "]:
                idx = result[:150].rfind(sep)
                if idx > 30:
                    result = result[:idx + 1]
                    break
            else:
                result = result[:147] + "..."

        return result

    def is_speaking(self) -> bool:
        return self._speaking

    def stop_speaking(self):
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def stop(self):
        self._stop_event.set()
        self._queue.put(None)

    def set_voice(self, voice: str):
        """Change the TTS voice (e.g. 'en-US-AriaNeural')."""
        self.voice = voice
