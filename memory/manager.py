"""
Aura-X Memory Manager
Orchestrates short-term conversation context + long-term vector memory + RAG.
"""

import time
import json
from typing import List, Dict, Optional
from pathlib import Path
from core.config import CONFIG
from core.logger import setup_logger
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory

logger = setup_logger("aura_x.memory.manager")

MEMORY_CONFIG = CONFIG.get("memory", {})


class MemoryManager:
    """Unified memory system combining short-term and long-term memory with RAG."""

    def __init__(self):
        # Short-term (conversation)
        self.short_term = ShortTermMemory(
            max_messages=MEMORY_CONFIG.get("short_term_max_messages", 30),
            summary_threshold=MEMORY_CONFIG.get("short_term_summary_threshold", 20)
        )

        # Long-term (persistent vector store)
        self.long_term_enabled = MEMORY_CONFIG.get("long_term_enabled", True)
        db_path = MEMORY_CONFIG.get("long_term_db_path", "data/memory_store")
        self.long_term = LongTermMemory(db_path) if self.long_term_enabled else None

        # RAG settings
        self.max_recall_results = MEMORY_CONFIG.get("max_recall_results", 5)
        self.auto_save_threshold = MEMORY_CONFIG.get("auto_save_threshold", 0.7)
        self._session_path = Path(CONFIG.get("log_dir", "logs")) / "session_memory.json"

        # Load saved session if exists
        self._load_session()

    def add_user_message(self, content: str):
        """Record a user message in short-term memory."""
        self.short_term.add_message("user", content)

    def add_assistant_message(self, content: str):
        """Record an assistant response in short-term memory."""
        self.short_term.add_message("assistant", content)

    def add_system_message(self, content: str):
        """Add a system-level context message."""
        self.short_term.add_message("system", content)

    def get_context_messages(self, system_prompt: str,
                             screen_context: str = "") -> List[Dict]:
        """Build the full message context for AI consumption with RAG recall."""
        messages = []

        # System prompt
        system_content = system_prompt
        if screen_context:
            system_content += f"\n\nCURRENT SCREEN CONTEXT:\n{screen_context}"

        # RAG: Retrieve relevant long-term memories
        last_user_msg = self.short_term.get_last_user_message()
        if last_user_msg and self.long_term_enabled and self.long_term:
            recalled = self.long_term.recall(
                last_user_msg,
                top_k=self.max_recall_results,
                min_score=0.15
            )
            if recalled:
                memory_context = "\n".join(
                    f"- [{m['category']}] {m['content']}"
                    for m in recalled
                )
                system_content += f"\n\nRELEVANT MEMORIES:\n{memory_context}"

        messages.append({"role": "system", "content": system_content})

        # Conversation context from short-term memory
        context = self.short_term.get_context()
        for msg in context:
            if msg["role"] != "system":  # Avoid duplicate system messages
                messages.append({"role": msg["role"], "content": msg["content"]})

        return messages

    def remember_interaction(self, user_msg: str, assistant_msg: str,
                             category: str = "conversation",
                             importance: float = 0.5):
        """Save an important interaction to long-term memory."""
        if not self.long_term_enabled or not self.long_term:
            return

        # Combine user question and response for richer recall
        content = f"User: {user_msg}\nAssistant: {assistant_msg}"
        if len(content) > 500:
            content = content[:500]

        self.long_term.remember(
            content=content,
            category=category,
            importance=importance
        )

    def auto_save_important(self, user_msg: str, assistant_msg: str):
        """Automatically determine if an interaction should be saved long-term."""
        if not self.long_term_enabled or not self.long_term:
            return

        # Heuristics for importance
        importance = 0.3

        # Longer, detailed interactions are more important
        combined_len = len(user_msg) + len(assistant_msg)
        if combined_len > 500:
            importance += 0.2
        if combined_len > 1000:
            importance += 0.1

        # Coding/technical content is valuable
        code_indicators = ['```', 'def ', 'class ', 'import ', 'function', 'error', 'bug', 'fix']
        combined = (user_msg + " " + assistant_msg).lower()
        if any(ind in combined for ind in code_indicators):
            importance += 0.2

        # Tool executions are important
        if '"tool"' in assistant_msg or '[Tool' in assistant_msg:
            importance += 0.15

        # Questions with detailed answers
        if '?' in user_msg and len(assistant_msg) > 200:
            importance += 0.1

        if importance >= self.auto_save_threshold:
            category = "coding" if any(
                ind in user_msg.lower() for ind in ['code', 'debug', 'error', 'function', 'script']
            ) else "conversation"
            self.remember_interaction(user_msg, assistant_msg, category, importance)

    def save(self):
        """Persist all memory to disk."""
        if self.long_term:
            self.long_term.save()
        self._save_session()

    def _save_session(self):
        """Save current session state for recovery."""
        try:
            session = self.short_term.to_dict()
            self._session_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._session_path, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=1)
        except Exception as e:
            logger.debug(f"Session save error: {e}")

    def _load_session(self):
        """Load previous session if exists."""
        try:
            if self._session_path.exists():
                with open(self._session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.short_term.from_dict(data)
                logger.info(f"Restored session: {len(self.short_term.messages)} messages")
        except Exception as e:
            logger.debug(f"Session load error: {e}")

    def clear_short_term(self):
        """Clear conversation context."""
        self.short_term.clear()

    def clear_all(self):
        """Clear all memory (use with caution)."""
        self.short_term.clear()
        if self.long_term:
            self.long_term.store.documents.clear()
            self.long_term.store.doc_vectors.clear()
            self.long_term.store.idf_scores.clear()
            self.long_term.save()

    def get_stats(self) -> Dict:
        stats = {
            "short_term": self.short_term.get_stats(),
            "long_term": self.long_term.get_stats() if self.long_term else {"disabled": True}
        }
        return stats
