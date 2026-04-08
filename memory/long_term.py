"""
Aura-X Long-Term Memory
FAISS-free vector store using TF-IDF for zero-dependency persistent memory.
"""

import os
import json
import time
import math
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from collections import Counter
from core.logger import setup_logger

logger = setup_logger("aura_x.memory.long_term")


class TFIDFVectorStore:
    """Simple TF-IDF based vector store for semantic search without heavy dependencies."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.documents: List[Dict] = []
        self.vocabulary: Dict[str, int] = {}
        self.idf_scores: Dict[str, float] = {}
        self.doc_vectors: List[Dict[str, float]] = []
        self._dirty = False
        self._load()

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase, split on non-alphanumeric."""
        text = text.lower()
        tokens = re.findall(r'\b[a-z][a-z0-9]{1,}\b', text)
        # Remove ultra-common stopwords
        stopwords = {
            'the', 'is', 'at', 'which', 'on', 'in', 'it', 'to', 'and', 'or',
            'of', 'for', 'with', 'as', 'by', 'an', 'be', 'this', 'that',
            'are', 'was', 'were', 'been', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can',
            'from', 'but', 'not', 'you', 'all', 'they', 'we', 'he', 'she',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'what', 'so'
        }
        return [t for t in tokens if t not in stopwords]

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Compute term frequency for a document."""
        counts = Counter(tokens)
        total = len(tokens) if tokens else 1
        return {word: count / total for word, count in counts.items()}

    def _rebuild_idf(self):
        """Rebuild the IDF scores from all documents."""
        n_docs = len(self.documents)
        if n_docs == 0:
            self.idf_scores = {}
            return

        doc_count: Dict[str, int] = {}
        for doc in self.documents:
            tokens = set(self._tokenize(doc.get("content", "")))
            for token in tokens:
                doc_count[token] = doc_count.get(token, 0) + 1

        self.idf_scores = {
            word: math.log((n_docs + 1) / (count + 1)) + 1
            for word, count in doc_count.items()
        }

        # Rebuild all document vectors
        self.doc_vectors = []
        for doc in self.documents:
            tokens = self._tokenize(doc.get("content", ""))
            tf = self._compute_tf(tokens)
            vector = {
                word: tf_val * self.idf_scores.get(word, 1.0)
                for word, tf_val in tf.items()
            }
            self.doc_vectors.append(vector)

    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """Compute cosine similarity between two sparse vectors."""
        common_keys = set(vec_a.keys()) & set(vec_b.keys())
        if not common_keys:
            return 0.0

        dot_product = sum(vec_a[k] * vec_b[k] for k in common_keys)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def add(self, content: str, metadata: Optional[Dict] = None) -> int:
        """Add a document to the store."""
        doc = {
            "id": len(self.documents),
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        self.documents.append(doc)
        self._dirty = True

        # Rebuild IDF periodically (every 10 additions) or if small collection
        if len(self.documents) <= 20 or len(self.documents) % 10 == 0:
            self._rebuild_idf()
        else:
            # Just compute the vector for the new document using existing IDF
            tokens = self._tokenize(content)
            tf = self._compute_tf(tokens)
            vector = {
                word: tf_val * self.idf_scores.get(word, 1.0)
                for word, tf_val in tf.items()
            }
            self.doc_vectors.append(vector)

        return doc["id"]

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """Search for similar documents."""
        if not self.documents:
            return []

        # Compute query vector
        tokens = self._tokenize(query)
        tf = self._compute_tf(tokens)
        query_vector = {
            word: tf_val * self.idf_scores.get(word, 1.0)
            for word, tf_val in tf.items()
        }

        # Score all documents
        scored = []
        for i, doc_vec in enumerate(self.doc_vectors):
            sim = self._cosine_similarity(query_vector, doc_vec)
            if sim > 0.05:  # Minimum threshold
                scored.append((self.documents[i], sim))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def delete(self, doc_id: int) -> bool:
        """Delete a document by ID."""
        for i, doc in enumerate(self.documents):
            if doc["id"] == doc_id:
                self.documents.pop(i)
                self.doc_vectors.pop(i)
                self._dirty = True
                return True
        return False

    def save(self):
        """Persist to disk."""
        if not self._dirty and self.db_path.exists():
            return
        try:
            data = {
                "documents": self.documents,
                "idf_scores": self.idf_scores,
            }
            save_path = self.db_path / "memory_store.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            self._dirty = False
            logger.debug(f"Saved {len(self.documents)} documents to long-term memory")
        except Exception as e:
            logger.error(f"Memory save error: {e}")

    def _load(self):
        """Load from disk."""
        save_path = self.db_path / "memory_store.json"
        if not save_path.exists():
            return
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.documents = data.get("documents", [])
            self.idf_scores = data.get("idf_scores", {})
            # Rebuild vectors from loaded data
            self._rebuild_idf()
            logger.info(f"Loaded {len(self.documents)} documents from long-term memory")
        except Exception as e:
            logger.error(f"Memory load error: {e}")

    def get_stats(self) -> Dict:
        return {
            "total_documents": len(self.documents),
            "vocabulary_size": len(self.idf_scores),
            "db_path": str(self.db_path)
        }


class LongTermMemory:
    """High-level interface for persistent long-term memory."""

    def __init__(self, db_path: str):
        self.store = TFIDFVectorStore(db_path)

    def remember(self, content: str, category: str = "general",
                 importance: float = 0.5, metadata: Optional[Dict] = None):
        """Store a memory."""
        meta = metadata or {}
        meta.update({
            "category": category,
            "importance": importance
        })
        self.store.add(content, meta)

    def recall(self, query: str, top_k: int = 5, min_score: float = 0.1) -> List[Dict]:
        """Recall relevant memories."""
        results = self.store.search(query, top_k=top_k)
        memories = []
        for doc, score in results:
            if score >= min_score:
                memories.append({
                    "content": doc["content"],
                    "score": round(score, 3),
                    "category": doc.get("metadata", {}).get("category", "general"),
                    "timestamp": doc.get("timestamp", 0)
                })
        return memories

    def save(self):
        self.store.save()

    def get_stats(self) -> Dict:
        return self.store.get_stats()
