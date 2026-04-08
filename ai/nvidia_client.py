import json
import requests
from typing import List, Dict, Optional
from core.config import CONFIG
from core.logger import setup_logger

logger = setup_logger("aura_x.ai.nvidia")

NVIDIA_BASE = CONFIG.get("nvidia_base_url", "https://integrate.api.nvidia.com/v1")
NVIDIA_API_KEY = CONFIG.get("nvidia_api_key", "")
NVIDIA_MODEL = CONFIG.get("nvidia_model", "meta/llama3-70b-instruct")


class NvidiaClient:
    def __init__(
        self,
        api_key: str = NVIDIA_API_KEY,
        base_url: str = NVIDIA_BASE,
        model: str = NVIDIA_MODEL
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._available = bool(api_key)

    def is_available(self) -> bool:
        return self._available

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        model: Optional[str] = None
    ) -> str:
        if not self.api_key:
            raise RuntimeError("NVIDIA API key not configured")

        use_model = model or self.model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9,
            "stream": False
        }

        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except requests.Timeout:
            raise TimeoutError("NVIDIA API timed out")
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                raise RuntimeError("Invalid NVIDIA API key")
            elif e.response.status_code == 429:
                raise RuntimeError("NVIDIA API rate limit exceeded")
            raise RuntimeError(f"NVIDIA HTTP error {e.response.status_code}: {e}")
        except KeyError:
            raise RuntimeError("Unexpected NVIDIA API response format")
        except Exception as e:
            raise RuntimeError(f"NVIDIA chat error: {e}")


class DeepSeekClient:
    """DeepSeek API client (OpenAI-compatible)."""

    def __init__(self, api_key: str = "", base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key or CONFIG.get("deepseek_api_key", "")
        self.base_url = base_url
        self._available = bool(self.api_key)

    def is_available(self) -> bool:
        return self._available

    def chat(
        self,
        messages: List[Dict],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        if not self.api_key:
            raise RuntimeError("DeepSeek API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"DeepSeek error: {e}")


_nvidia_client: Optional[NvidiaClient] = None
_deepseek_client: Optional[DeepSeekClient] = None


def get_nvidia_client() -> NvidiaClient:
    global _nvidia_client
    if _nvidia_client is None:
        _nvidia_client = NvidiaClient()
    return _nvidia_client


def get_deepseek_client() -> DeepSeekClient:
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client
