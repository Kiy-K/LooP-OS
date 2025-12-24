# kernel/memory.py
"""
Persistent Memory System.

This module provides semantic memory capabilities using ChromaDB,
allowing agents to store and recall information across sessions.
"""

import os
import threading
import time
import hashlib
import json
from pathlib import Path

# Try to import ChromaDB, but handle failure gracefully for testing if needed
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

class MemoryManager:
    """
    Manages persistent semantic memory for the agent.

    Attributes:
        client: The ChromaDB client.
        collection: The memory collection.
    """

    # Configuration
    MAX_MEMORY_ITEMS = 100000  # Prevent memory overflow

    def __init__(self, persistence_path=None):
        """
        Initialize the MemoryManager.

        Args:
            persistence_path (str, optional): Path to store the database.
                                              Defaults to ~/.loop/memory.
        """
        if not persistence_path:
            persistence_path = str(Path.home() / ".loop" / "memory")

        self.persistence_path = persistence_path
        os.makedirs(persistence_path, exist_ok=True)

        self.lock = threading.RLock()
        self.client = None
        self.collection = None

        if HAS_CHROMA:
            try:
                self.client = chromadb.PersistentClient(path=persistence_path)
                self.collection = self.client.get_or_create_collection(name="agent_memory")
            except Exception as e:
                print(f"Warning: Failed to initialize ChromaDB: {e}")

    def store(self, content, metadata=None):
        """
        Store a memory.

        Args:
            content (str): The text content to store.
            metadata (dict, optional): Additional metadata.

        Returns:
            str: Document ID if successful, False otherwise.
        """
        if not HAS_CHROMA or not self.collection:
            return False

        if not content or not isinstance(content, str):
            return False

        # Input Sanitization: Ensure content is string and reasonably safe
        content = content.replace("\0", "")

        with self.lock:
            # Check resource limit - count is potentially expensive?
            # ChromaDB count() is usually fast.
            # However, if count() is cached or stale, we might overshoot.
            count = self.collection.count()
            if count >= self.MAX_MEMORY_ITEMS:
                raise RuntimeError(f"Memory Limit Exceeded: {count} >= {self.MAX_MEMORY_ITEMS}")

            # Generate ID
            if metadata:
                 # Clean metadata
                 clean_meta = {}
                 for k, v in metadata.items():
                     if isinstance(v, (str, int, float, bool)):
                         clean_meta[k] = v
                     else:
                         clean_meta[k] = str(v)
                 metadata = clean_meta
            else:
                metadata = {}

            if "timestamp" not in metadata:
                metadata["timestamp"] = time.time()

            doc_id = hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()

            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            return doc_id

    def recall(self, query, n_results=5):
        """
        Recall memories relevant to a query.

        Args:
            query (str): The search query.
            n_results (int): Number of results to return.

        Returns:
            list[dict]: A list of memory objects.
        """
        if not HAS_CHROMA or not self.collection:
            return []

        with self.lock:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
            except Exception as e:
                # Handle case where n_results > count
                if "n_results" in str(e):
                     return []
                return []

            memories = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    meta = results['metadatas'][0][i] if results['metadatas'] else {}
                    memories.append({
                        "content": doc,
                        "metadata": meta,
                        "id": results['ids'][0][i]
                    })

            return memories

    def delete(self, key_id=None, query=None):
        """
        Delete a memory by ID or query.
        """
        if not HAS_CHROMA or not self.collection:
            return False

        with self.lock:
            if key_id:
                self.collection.delete(ids=[key_id])
                return True
            if query:
                # Find IDs first
                results = self.recall(query, n_results=10)
                ids = [m["id"] for m in results]
                if ids:
                    self.collection.delete(ids=ids)
                    return len(ids)
            return False

    def clear(self):
        """
        Clear all memories.
        """
        if not HAS_CHROMA or not self.client:
            return False

        with self.lock:
            self.client.delete_collection("agent_memory")
            self.collection = self.client.get_or_create_collection(name="agent_memory")
            return True

    def count(self):
        """
        Return number of memories.
        """
        if not HAS_CHROMA or not self.collection:
            return 0
        with self.lock:
            return self.collection.count()
