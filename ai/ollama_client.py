import json
import requests
from typing import List, Dict, Optional, Generator
from core.config import CONFIG
from core.logger import setup_logger

logger = setup_logger("aura_x.ai.ollama")

OLLAMA_BASE = CONFIG.get("ollama_base_url", "http://localhost:11434")


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE):
        self.base_url = base_url.rstrip("/")
        self._available_models: Optional[List[str]] = None
        self._healthy: Optional[bool] = None
        self._health_checked_at: float = 0

    def is_healthy(self) -> bool:
        """Check if Ollama is reachable. Refreshes every 30 seconds."""
        import time
        now = time.time()
        if self._healthy is not None and (now - self._health_checked_at) < 30:
            return self._healthy
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            self._healthy = r.status_code == 200
        except Exception:
            self._healthy = False
        self._health_checked_at = now
        return self._healthy

    def refresh_health(self):
        """Force health re-check."""
        self._healthy = None
        self._health_checked_at = 0
        self._available_models = None

    def list_models(self) -> List[str]:
        if self._available_models is not None:
            return self._available_models
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                data = r.json()
                self._available_models = [m["name"] for m in data.get("models", [])]
                return self._available_models
        except Exception as e:
            logger.debug(f"Ollama list models error: {e}")
        self._available_models = []
        return []

    def model_available(self, model_name: str) -> bool:
        return self.resolve_model_name(model_name) is not None

    def resolve_model_name(self, requested_model: str) -> Optional[str]:
        """Resolve a configured model alias to an actually installed Ollama model tag."""
        available = self.list_models()
        if not available:
            return None

        target = (requested_model or "").strip().lower()
        if not target:
            return None

        # 1) Exact match
        for model in available:
            if model.lower() == target:
                return model

        # 2) Tagged variants (model:7b, model:8b)
        for model in available:
            if model.lower().startswith(f"{target}:"):
                return model

        # 3) Prefix/contains fallback
        for model in available:
            lower_model = model.lower()
            if lower_model.startswith(target) or target in lower_model:
                return model

        return None

    def chat(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> str:
        """Send a chat request and return the full response."""
        if not self.is_healthy():
            raise ConnectionError("Ollama service not available")

        resolved_model = self.resolve_model_name(model)
        if resolved_model is not None:
            model = resolved_model
        else:
            available = self.list_models()
            if available:
                requested_model = model
                model = available[0]
                logger.warning(f"Model '{requested_model}' not installed; falling back to {model}")
            else:
                raise RuntimeError("No Ollama models available")

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9
            }
        }

        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120
            )
            r.raise_for_status()
            data = r.json()
            return data.get("message", {}).get("content", "")
        except requests.Timeout:
            raise TimeoutError("Ollama request timed out")
        except requests.HTTPError as e:
            detail = ""
            try:
                body = r.json()
                detail = body.get("error", "")
            except Exception:
                detail = r.text[:200] if r is not None else ""
            if detail:
                raise RuntimeError(f"Ollama HTTP error: {e}. Detail: {detail}")
            raise RuntimeError(f"Ollama HTTP error: {e}")
        except Exception as e:
            raise RuntimeError(f"Ollama chat error: {e}")

    def stream_chat(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Generator[str, None, None]:
        """Stream chat response token-by-token."""
        if not self.is_healthy():
            raise ConnectionError("Ollama service not available")

        resolved_model = self.resolve_model_name(model)
        if resolved_model:
            model = resolved_model
        else:
            available = self.list_models()
            if available:
                model = available[0]
            else:
                raise RuntimeError("No Ollama models available")

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9
            }
        }

        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
                stream=True
            )
            r.raise_for_status()

            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise RuntimeError(f"Ollama stream error: {e}")

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        if not self.is_healthy():
            raise ConnectionError("Ollama service not available")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            r.raise_for_status()
            data = r.json()
            return data.get("response", "")
        except Exception as e:
            raise RuntimeError(f"Ollama generate error: {e}")

    def pull_model(self, model: str) -> bool:
        try:
            logger.info(f"Pulling model: {model}")
            r = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=600,
                stream=True
            )
            for line in r.iter_lines():
                if line:
                    data = json.loads(line)
                    if "error" in data:
                        logger.error(f"Pull error: {data['error']}")
                        return False
            self._available_models = None
            return True
        except Exception as e:
            logger.error(f"Model pull error: {e}")
            return False


_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
