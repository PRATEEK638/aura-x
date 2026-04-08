import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "aura_x_config.json"
DATA_DIR = BASE_DIR / "data"

DEFAULT_CONFIG = {
    "assistant_name": "Aura-X",
    "wake_word": "aura",
    "voice_enabled": True,
    "voice_rate": 175,
    "voice_volume": 1.0,
    "voice_index": 0,
    "screenshot_interval": 0.5,
    "ocr_lang": "eng",
    "ollama_base_url": "http://localhost:11434",
    "models": {
        "fast": "phi3:mini",
        "general": "llama3",
        "coding": "qwen2.5-coder",
        "reasoning": "llama3",
        "fallback": "llama3"
    },
    "nvidia_api_key": os.getenv("NVIDIA_API_KEY", ""),
    "nvidia_base_url": "https://integrate.api.nvidia.com/v1",
    "nvidia_model": "meta/llama3-70b-instruct",
    "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "permission_level": "interactive",
    "log_dir": str(BASE_DIR / "logs"),
    "memory": {
        "short_term_max_messages": 30,
        "short_term_summary_threshold": 20,
        "long_term_enabled": True,
        "long_term_db_path": str(DATA_DIR / "memory_store"),
        "embedding_method": "tfidf",
        "max_recall_results": 5,
        "auto_save_threshold": 0.7
    },
    "agent": {
        "max_steps": 15,
        "step_timeout": 60,
        "auto_verify": True,
        "retry_on_failure": True,
        "max_retries": 2
    },
    "gui": {
        "theme": "dark",
        "accent_color": "#00D4FF",
        "secondary_accent": "#A855F7",
        "font_family": "Segoe UI",
        "font_size": 13,
        "window_width": 1100,
        "window_height": 750,
        "opacity": 0.97,
        "animations_enabled": True
    },
    "organize_rules": {
        "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff"],
        "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md"],
        "videos": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"],
        "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
        "code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs", ".go",
                 ".rb", ".php", ".html", ".css", ".sh", ".bat", ".ps1"],
        "archives": [".zip", ".tar", ".gz", ".rar", ".7z", ".bz2"],
        "spreadsheets": [".xlsx", ".xls", ".csv", ".ods"],
        "presentations": [".pptx", ".ppt", ".odp"],
        "executables": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm"]
    },
    "safe_commands": ["ls", "dir", "pwd", "echo", "cat", "type", "find", "grep",
                      "python", "python3", "pip", "git status", "git log"],
    "blocked_commands": ["rm -rf /", "format", "del /f /s /q c:\\",
                         "shutdown", "reboot", "mkfs"],
    "screen_monitor": True,
    "screen_monitor_fps": 2,
    "tool_history_limit": 100
}


def load_config() -> dict:
    """Load config from aura_x_config.json, merging with defaults."""
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
            merged = _deep_merge(DEFAULT_CONFIG.copy(), loaded)
            return merged
        except Exception:
            pass
    # Try legacy config
    legacy = BASE_DIR / "jarvis_config.json"
    if legacy.exists():
        try:
            with open(legacy, "r") as f:
                loaded = json.load(f)
            merged = _deep_merge(DEFAULT_CONFIG.copy(), loaded)
            # Migrate: save as new config
            save_config(merged)
            return merged
        except Exception:
            pass
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def save_config(config: dict):
    """Save config to aura_x_config.json."""
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_config_value(key_path: str, default=None):
    """Get a nested config value using dot notation: 'gui.theme'"""
    keys = key_path.split(".")
    value = CONFIG
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
        if value is None:
            return default
    return value


CONFIG = load_config()
