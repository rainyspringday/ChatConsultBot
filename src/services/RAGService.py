import os
from pathlib import Path
from groq import Groq

from src.services.TextChunkerService import TextChunkerService
from src.services.ChunkSearchService import ChunkSearchService
from src.core.config import Config


class RAGService:
    def __init__(
        self,
        chunker: TextChunkerService,
        search: ChunkSearchService
    ):

        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.chunker = chunker
        self.search = search

        self.text = self._load_documents()
        chunks=self.chunker.chunk_text(self.text)
        self.search.build(chunks)


    def _load_documents(self) -> str:
        """Load all cleaned documents into one text blob"""
        text = ""

        project_root = Path(__file__).parent.parent.parent
        cleaned_folder = project_root / Config.output_dir

        for file in Path(cleaned_folder).glob("*_cleaned.txt"):
            text += f"\n\n--- {file.name} ---\n"
            text += file.read_text(encoding="utf-8")

        return text

    def ask(self, question: str) -> str:
        """Main RAG pipeline"""

        relevant_chunks = self.search.find_relevant(question)
        context = "\n\n".join(chunk["text"] for chunk in relevant_chunks)

        if not context:
            return "❌ No relevant information found in the documents."

        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "Business consultant. Answer ONLY from provided context."
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {question}"
                }
            ]
        )

        return response.choices[0].message.content