import logging
import os
import json
import queue
from datetime import datetime
from pathlib import Path
from core.config import CONFIG

LOG_DIR = Path(CONFIG["log_dir"])
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / f"aura_x_{datetime.now().strftime('%Y%m%d')}.log"
ACTION_LOG_FILE = LOG_DIR / "actions.jsonl"

# Global log queue for GUI log panel
_log_queue: queue.Queue = queue.Queue(maxsize=500)


class QueueHandler(logging.Handler):
    """Sends log records to a queue for GUI consumption."""

    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self._queue = log_queue

    def emit(self, record):
        try:
            entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "level": record.levelname,
                "name": record.name.replace("aura_x.", ""),
                "message": self.format(record)
            }
            # Non-blocking put
            try:
                self._queue.put_nowait(entry)
            except queue.Full:
                # Drop oldest
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                self._queue.put_nowait(entry)
        except Exception:
            pass


def setup_logger(name: str) -> logging.Logger:
    """Create a logger that writes to file, console, and GUI queue."""
    # Migrate old logger names
    name = name.replace("jarvis.", "aura_x.")
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Console handler (minimal)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    # GUI queue handler
    qh = QueueHandler(_log_queue)
    qh.setLevel(logging.DEBUG)
    qh.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.addHandler(qh)
    return logger


def get_log_queue() -> queue.Queue:
    """Get the shared log queue for GUI consumption."""
    return _log_queue


def log_action(tool: str, params: dict, result: str, status: str, risk: str):
    """Log a tool action to the actions JSONL file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool,
        "params": params,
        "result": result,
        "status": status,
        "risk": risk
    }
    try:
        with open(ACTION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def get_action_history(limit: int = 50) -> list:
    """Read recent actions from the JSONL log."""
    history = []
    try:
        if ACTION_LOG_FILE.exists():
            with open(ACTION_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    history.append(json.loads(line.strip()))
                except Exception:
                    pass
    except Exception:
        pass
    return history


logger = setup_logger("aura_x.core")
