"""
Aura-X Short-Term Memory
Manages conversation context with smart truncation and summarization.
"""

import time
from typing import List, Dict, Optional
from core.logger import setup_logger

logger = setup_logger("aura_x.memory.short_term")


class ShortTermMemory:
    """Conversation context window with token-aware management."""

    def __init__(self, max_messages: int = 30, summary_threshold: int = 20):
        self.max_messages = max_messages
        self.summary_threshold = summary_threshold
        self.messages: List[Dict] = []
        self.summaries: List[str] = []
        self._total_interactions = 0

    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self._total_interactions += 1

        # Auto-summarize when threshold is reached
        if len(self.messages) > self.max_messages:
            self._compact()

    def get_context(self, max_messages: Optional[int] = None) -> List[Dict]:
        """Get conversation context for AI consumption."""
        limit = max_messages or self.max_messages
        context = []

        # Include summary of older messages if available
        if self.summaries:
            combined_summary = " ".join(self.summaries[-3:])
            context.append({
                "role": "system",
                "content": f"[Previous conversation summary: {combined_summary}]"
            })

        # Include recent messages
        recent = self.messages[-limit:]
        for msg in recent:
            context.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        return context

    def _compact(self):
        """Summarize older messages and keep only recent ones."""
        if len(self.messages) <= self.summary_threshold:
            return

        # Take the older half of messages to summarize
        split_point = len(self.messages) - self.summary_threshold
        old_messages = self.messages[:split_point]

        # Create a simple extractive summary
        summary_parts = []
        for msg in old_messages:
            role = msg["role"]
            text = msg["content"]
            if len(text) > 150:
                text = text[:150] + "..."
            if role == "user":
                summary_parts.append(f"User asked: {text}")
            elif role == "assistant":
                summary_parts.append(f"Assistant: {text}")

        if summary_parts:
            summary = "; ".join(summary_parts[-6:])  # Keep last 6 interactions
            self.summaries.append(summary)
            # Keep only last 5 summaries
            if len(self.summaries) > 5:
                self.summaries = self.summaries[-5:]

        # Trim to recent messages only
        self.messages = self.messages[split_point:]
        logger.debug(f"Compacted memory: kept {len(self.messages)} messages, {len(self.summaries)} summaries")

    def get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message."""
        for msg in reversed(self.messages):
            if msg["role"] == "user":
                return msg["content"]
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the most recent assistant message."""
        for msg in reversed(self.messages):
            if msg["role"] == "assistant":
                return msg["content"]
        return None

    def clear(self):
        """Clear all short-term memory."""
        self.messages.clear()
        self.summaries.clear()
        self._total_interactions = 0

    def get_stats(self) -> Dict:
        return {
            "current_messages": len(self.messages),
            "summaries": len(self.summaries),
            "total_interactions": self._total_interactions
        }

    def to_dict(self) -> Dict:
        return {
            "messages": self.messages,
            "summaries": self.summaries,
            "total_interactions": self._total_interactions
        }

    def from_dict(self, data: Dict):
        self.messages = data.get("messages", [])
        self.summaries = data.get("summaries", [])
        self._total_interactions = data.get("total_interactions", 0)
