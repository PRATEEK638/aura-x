"""
Aura-X Core Assistant
Central orchestrator — connects AI, Agent, Memory, Perception, and Tools.
Exposes a clean API for both CLI and GUI.
"""

import threading
from typing import Optional, Generator
from core.config import CONFIG
from core.logger import setup_logger
from core.permissions import get_permission_system
from ai.router import AIRouter
from tools.executor import ToolExecutor
from memory.manager import MemoryManager
from core.agent import AgentLoop, SYSTEM_PROMPT

logger = setup_logger("aura_x.core.assistant")


class AuraXAssistant:
    """The central brain of Aura-X."""

    def __init__(self):
        self.config = CONFIG
        self.name = self.config["assistant_name"]
        self.running = False

        # Core systems
        self.ai_router = AIRouter()
        self.tool_executor = ToolExecutor()
        self.memory_manager = MemoryManager()
        self.permission_system = get_permission_system()

        # Screen monitor (optional)
        self.screen_monitor = None
        self._init_screen_monitor()

        # Perception system (optional)
        self.perception = None
        self._init_perception()

        # Agent loop — does ALL reasoning + tool execution
        self.agent_loop = AgentLoop(
            ai_router=self.ai_router,
            tool_executor=self.tool_executor,
            memory_manager=self.memory_manager,
            perception=self.perception
        )

        # Voice (optional — initialized by caller)
        self.speaker = None
        self._init_voice()

        self._processing = False

    def _init_screen_monitor(self):
        try:
            from vision.screen_capture import ScreenMonitor
            self.screen_monitor = ScreenMonitor(
                interval=self.config.get("screenshot_interval", 0.5),
                enabled=self.config.get("screen_monitor", True)
            )
        except Exception as e:
            logger.info(f"Screen monitor disabled: {e}")

    def _init_perception(self):
        try:
            from core.perception import PerceptionSystem
            self.perception = PerceptionSystem(screen_monitor=self.screen_monitor)
        except Exception as e:
            logger.info(f"Perception system disabled: {e}")

    def _init_voice(self):
        if self.config.get("voice_enabled", True):
            try:
                from voice.speaker import VoiceSpeaker
                self.speaker = VoiceSpeaker()
            except Exception as e:
                logger.info(f"Voice output disabled: {e}")

    def start(self):
        self.running = True
        if self.screen_monitor and self.screen_monitor.enabled:
            threading.Thread(
                target=self.screen_monitor.start,
                daemon=True, name="ScreenMonitor"
            ).start()
        logger.info(f"{self.name} started successfully")

    def stop(self):
        self.running = False
        if self.screen_monitor:
            self.screen_monitor.stop()
        if self.speaker:
            self.speaker.stop()
        self.memory_manager.save()
        logger.info(f"{self.name} stopped")

    def process_input(self, user_text: str) -> str:
        """Process user input through the agent loop. Returns response text."""
        self._processing = True
        try:
            # Add to memory
            self.memory_manager.add_user_message(user_text)

            # Get screen context
            screen_context = ""
            if self.perception:
                screen_context = self.perception.get_context_summary()
            elif self.screen_monitor:
                screen_context = self.screen_monitor.get_context_summary()

            # Process through agent loop (handles EVERYTHING — reasoning + tools)
            response = self.agent_loop.process_input(user_text, screen_context)

            # Save response to memory
            self.memory_manager.add_assistant_message(response)
            self.memory_manager.auto_save_important(user_text, response)
            self.memory_manager.save()

            return response

        except Exception as e:
            logger.error(f"Process input error: {e}", exc_info=True)
            return f"Error aa gaya: {e}"
        finally:
            self._processing = False

    def stream_response(self, user_text: str) -> Generator[str, None, None]:
        """Stream response for real-time display."""
        self.memory_manager.add_user_message(user_text)

        screen_context = ""
        if self.perception:
            screen_context = self.perception.get_context_summary()

        messages = self.memory_manager.get_context_messages(
            system_prompt=SYSTEM_PROMPT,
            screen_context=screen_context
        )

        full_response = ""
        try:
            for chunk in self.ai_router.stream_response(user_text, messages, screen_context):
                full_response += chunk
                yield chunk
        except Exception as e:
            yield f"\n\n⚠ Streaming error: {e}"

        if full_response:
            self.memory_manager.add_assistant_message(full_response)
            self.memory_manager.auto_save_important(user_text, full_response)

    def get_system_status(self) -> dict:
        return {
            "name": self.name,
            "running": self.running,
            "ai_stats": self.ai_router.get_stats(),
            "memory_stats": self.memory_manager.get_stats(),
            "screen_monitor": self.screen_monitor is not None,
            "perception": self.perception is not None,
            "voice": self.speaker is not None,
            "tools": self.tool_executor.list_tools()
        }

    @property
    def is_processing(self) -> bool:
        return self._processing
