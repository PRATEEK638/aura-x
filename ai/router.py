import time
from typing import List, Dict, Optional, Generator
from core.config import CONFIG
from core.logger import setup_logger
from ai.intent_classifier import classify_intent, get_model_for_intent, analyze_complexity
from ai.ollama_client import get_ollama_client
from ai.nvidia_client import get_nvidia_client, get_deepseek_client

logger = setup_logger("aura_x.ai.router")

MODELS = CONFIG.get("models", {})


class AIRouter:
    """
    Intelligent model router with phi3:mini for fast tasks.

    Routing Strategy:
    - phi3:mini  → fast commands, simple UI tasks, greetings
    - llama3:8b  → general reasoning, planning, conversation
    - qwen2.5-coder:7b → coding, debugging, code generation
    - NVIDIA cloud → complex reasoning, large context tasks
    """

    def __init__(self):
        self.ollama = get_ollama_client()
        self.nvidia = get_nvidia_client()
        self.deepseek = get_deepseek_client()
        self._stats = {
            "phi3": {"calls": 0, "errors": 0, "total_ms": 0},
            "llama3": {"calls": 0, "errors": 0, "total_ms": 0},
            "qwen": {"calls": 0, "errors": 0, "total_ms": 0},
            "nvidia": {"calls": 0, "errors": 0, "total_ms": 0},
            "deepseek": {"calls": 0, "errors": 0, "total_ms": 0}
        }
        self._last_model_used: str = ""
        self._last_error: Optional[str] = None

        # Pre-check which models are actually available
        self._available_models: set = set()
        try:
            if self.ollama.is_healthy():
                for m in self.ollama.list_models():
                    self._available_models.add(m.lower())
                logger.info(f"Available Ollama models: {self._available_models}")
        except Exception:
            pass

    def route_and_respond(
        self,
        text: str,
        messages: List[Dict],
        screen_context: str = ""
    ) -> str:
        """Route to the optimal model and get a response."""
        intent, confidence = classify_intent(text)
        complexity = analyze_complexity(text)
        model_type = get_model_for_intent(intent)

        logger.info(f"Intent: {intent} ({confidence:.2f}), Complexity: {complexity}, Route: {model_type}")

        # ─── Fast path: phi3 for simple automation/screen tasks only ───
        if complexity == "simple" and intent in ("automation", "screen"):
            response = self._try_ollama(messages, MODELS.get("fast", "phi3:mini"), "phi3")
            if response:
                return response

        # ─── Coding: qwen2.5-coder (complex → try NVIDIA first) ───
        if intent == "coding":
            if complexity == "complex":
                response = self._try_nvidia(messages)
                if response:
                    return response
            response = self._try_ollama(messages, MODELS.get("coding", "qwen2.5-coder"), "qwen")
            if response:
                return response

        # ─── Complex reasoning: NVIDIA → DeepSeek → local ───
        if complexity == "complex":
            response = self._try_nvidia(messages)
            if response:
                return response
            response = self._try_deepseek(messages)
            if response:
                return response

        # ─── Default: full fallback chain ───
        return self._fallback_chain(messages, model_type)

    def stream_response(
        self,
        text: str,
        messages: List[Dict],
        screen_context: str = ""
    ) -> Generator[str, None, None]:
        """Stream response token by token for real-time display."""
        intent, confidence = classify_intent(text)
        complexity = analyze_complexity(text)

        # Select model
        if complexity == "simple" and intent in ("automation", "screen"):
            model = MODELS.get("fast", "phi3:mini")
        elif intent == "coding":
            model = MODELS.get("coding", "qwen2.5-coder")
        else:
            model = MODELS.get("general", "llama3")

        # Try streaming from Ollama
        try:
            if self.ollama.is_healthy():
                yield from self.ollama.stream_chat(model=model, messages=messages)
                return
        except Exception as e:
            logger.warning(f"Stream error for {model}: {e}")

        # Fallback to non-streaming
        response = self.route_and_respond(text, messages, screen_context)
        yield response

    def _fallback_chain(self, messages: List[Dict], model_type: str) -> str:
        """Try models in order until one succeeds."""
        model_name = MODELS.get(model_type, MODELS.get("general", "llama3"))

        # Try 1: Primary local Ollama model
        response = self._try_ollama(messages, model_name, model_type)
        if response:
            return response

        # Try 2: General/fallback Ollama model
        fallback = MODELS.get("fallback", "llama3")
        if fallback != model_name:
            response = self._try_ollama(messages, fallback, "llama3")
            if response:
                return response

        # Try 3: Fast model (phi3) as last local option
        fast_model = MODELS.get("fast", "phi3:mini")
        if fast_model != model_name and fast_model != fallback:
            response = self._try_ollama(messages, fast_model, "phi3")
            if response:
                return response

        # Try 4: NVIDIA cloud
        response = self._try_nvidia(messages)
        if response:
            return response

        # Try 5: DeepSeek
        response = self._try_deepseek(messages)
        if response:
            return response

        return (
            "I'm sorry, I couldn't process that request. "
            "Please ensure Ollama is running locally (`ollama serve`) "
            "or configure a cloud API key in settings."
        )

    def _try_ollama(self, messages: List[Dict], model: str,
                     stat_key: str = "llama3") -> Optional[str]:
        """Try a local Ollama model."""
        start = time.time()
        try:
            if not self.ollama.is_healthy():
                return None
            response = self.ollama.chat(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            elapsed = int((time.time() - start) * 1000)
            safe_key = stat_key if stat_key in self._stats else "llama3"
            self._stats[safe_key]["calls"] += 1
            self._stats[safe_key]["total_ms"] += elapsed
            self._last_model_used = f"ollama/{model}"
            logger.debug(f"Ollama ({model}) responded in {elapsed}ms")
            return response if response else None
        except Exception as e:
            safe_key = stat_key if stat_key in self._stats else "llama3"
            self._stats[safe_key]["errors"] += 1
            logger.warning(f"Ollama ({model}) failed: {e}")
            return None

    def _try_nvidia(self, messages: List[Dict]) -> Optional[str]:
        """Try NVIDIA cloud API."""
        if not self.nvidia.is_available():
            return None
        start = time.time()
        try:
            response = self.nvidia.chat(messages=messages, temperature=0.7)
            elapsed = int((time.time() - start) * 1000)
            self._stats["nvidia"]["calls"] += 1
            self._stats["nvidia"]["total_ms"] += elapsed
            self._last_model_used = "nvidia/cloud"
            logger.debug(f"NVIDIA responded in {elapsed}ms")
            return response if response else None
        except Exception as e:
            self._stats["nvidia"]["errors"] += 1
            logger.warning(f"NVIDIA failed: {e}")
            return None

    def _try_deepseek(self, messages: List[Dict]) -> Optional[str]:
        """Try DeepSeek cloud API."""
        if not self.deepseek.is_available():
            return None
        start = time.time()
        try:
            response = self.deepseek.chat(messages=messages)
            elapsed = int((time.time() - start) * 1000)
            self._stats["deepseek"]["calls"] += 1
            self._stats["deepseek"]["total_ms"] += elapsed
            self._last_model_used = "deepseek/cloud"
            logger.debug(f"DeepSeek responded in {elapsed}ms")
            return response if response else None
        except Exception as e:
            self._stats["deepseek"]["errors"] += 1
            logger.warning(f"DeepSeek failed: {e}")
            return None

    def get_stats(self) -> dict:
        result = {}
        for provider, stats in self._stats.items():
            avg_ms = stats["total_ms"] // max(stats["calls"], 1)
            result[provider] = {
                **stats,
                "avg_latency_ms": avg_ms,
                "error_rate": f"{stats['errors']/max(stats['calls'],1)*100:.1f}%"
            }
        result["last_model"] = self._last_model_used
        return result

    def get_last_model(self) -> str:
        return self._last_model_used

    def quick_classify(self, text: str) -> str:
        intent, _ = classify_intent(text)
        return intent
