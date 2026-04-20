from pathlib import Path

import chromadb

from src.core.config import Config


class ChromaStorageService:
    def __init__(self, persist_dir=None, collection_name="chunks"):
        if persist_dir is None:
            persist_dir = Path(Config.chroma_dir)
        self.client = chromadb.PersistentClient(path=persist_dir)

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks):
        self.collection.add(
            ids=[f"chunk_{c['chunk_id']}" for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[{"size": c["size"]} for c in chunks]
        )

    def search(self, query: str, n_results: int = 3):
        return self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
