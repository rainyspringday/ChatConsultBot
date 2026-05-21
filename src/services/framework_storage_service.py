from pathlib import Path
from typing import List, Dict
import uuid

from src.core.config import Config
from src.services.chroma_storage_service import ChromaStorageService
from src.services.text_chunker_service import TextChunkerService


class FrameworkIngestionService:
    def __init__(
        self,
        framework_dir: Path | None = None,
        collection_name: str = "business_frameworks",
        chunk_size: int = 1000,
        overlap: int = 100,
    ):
        self.framework_dir = Config.frameworks_dir
        self.chunker = TextChunkerService(chunk_size=chunk_size, overlap=overlap)
        self.chroma = ChromaStorageService(collection_name=collection_name)

    def load_framework_files(self) -> List[tuple[str, str]]:
        files = list(Path(self.framework_dir).glob("*.md"))
        frameworks = []

        for file in files:
            text = file.read_text(encoding="utf-8").strip()
            if text:
                frameworks.append((file.name, text))

        return frameworks

    def chunk_framework(self, filename: str, text: str) -> List[Dict]:
        chunks = self.chunker.chunk_text(text)

        for chunk in chunks:
            # 100% unique ID
            chunk["id"] = f"{filename}_{chunk['chunk_id']}_{uuid.uuid4().hex}"
            chunk["source"] = filename

        return chunks

    def ingest(self) -> int:
        frameworks = self.load_framework_files()
        all_chunks = []

        for filename, text in frameworks:
            chunks = self.chunk_framework(filename, text)
            all_chunks.extend(chunks)

        # Extract fields for Chroma
        ids = [c["id"] for c in all_chunks]
        documents = [c["text"] for c in all_chunks]
        metadatas = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in all_chunks]

        print("Sample IDs:")
        for i in ids[:10]:
            print(i)

        # Now pass correct lists to Chroma
        self.chroma.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        return len(all_chunks)


if __name__ == "__main__":
    service = FrameworkIngestionService()
    count = service.ingest()
    print(f"Ingested {count} framework chunks.")
