# kernel/memory.py
"""
Persistent Memory System.

This module provides semantic memory capabilities using ChromaDB,
allowing agents to store and recall information across sessions.
"""

import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
import json

class MemoryManager:
    """
    Manages persistent semantic memory for the agent.

    Attributes:
        client: The ChromaDB client.
        collection: The memory collection.
    """
    def __init__(self, persistence_path=None):
        """
        Initialize the MemoryManager.

        Args:
            persistence_path (str, optional): Path to store the database.
                                              Defaults to ~/.fyodor/memory.
        """
        if not persistence_path:
            persistence_path = str(Path.home() / ".fyodor" / "memory")

        os.makedirs(persistence_path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persistence_path)

        # Create or get the collection
        self.collection = self.client.get_or_create_collection(name="agent_memory")

    def store(self, content, metadata=None):
        """
        Store a memory.

        Args:
            content (str): The text content to store.
            metadata (dict, optional): Additional metadata (e.g., source, timestamp).
                                       Must be flat dictionary with string/int/float values.
        """
        if not content:
            return False

        # Generate a unique ID (or let Chroma handle it, but we need one)
        # We'll use a simple timestamp-based ID or content hash
        import hashlib
        import time

        # Clean metadata for ChromaDB (no nested dicts allowed usually)
        if metadata:
             # Convert non-primitive values to strings
             clean_meta = {}
             for k, v in metadata.items():
                 if isinstance(v, (str, int, float, bool)):
                     clean_meta[k] = v
                 else:
                     clean_meta[k] = str(v)
             metadata = clean_meta
        else:
            metadata = {}

        # Add timestamp if not present
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
            list[dict]: A list of memory objects (content, metadata).
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )

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

    def clear(self):
        """
        Clear all memories.
        """
        self.client.delete_collection("agent_memory")
        self.collection = self.client.get_or_create_collection(name="agent_memory")
        return True

    def count(self):
        """
        Return number of memories.
        """
        return self.collection.count()
