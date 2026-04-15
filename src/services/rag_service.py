import os
from pathlib import Path
from groq import Groq
from src.services.text_chunker_service import TextChunkerService
from src.services.chunk_search_service import ChunkSearchService
from src.core.config import Config
import json


class RAGService:
    def __init__(
        self,
        chunker: TextChunkerService,
        search: ChunkSearchService,

    ):

        self.chunker = chunker
        self.search = search
        self.text = ""
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        graph_path = Config.graph_dir / "graph.json"
        with graph_path.open("r", encoding="utf-8") as f:
            self.graph = json.load(f)


    def build(self):
        self.text = self._load_documents()
        chunks = self.chunker.chunk_text(self.text)
        self.search.build(chunks)

    def get_graph_context(self, query: str) -> str:
        query = query.lower()

        nodes = self.graph.get("nodes", [])

        return "\n".join(
            n["text"]
            for n in nodes
            if query in n["text"].lower()
        )


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
        graph_context = self.get_graph_context(question)
        vector_context = "\n\n".join(chunk["text"] for chunk in relevant_chunks)

        if not relevant_chunks and not graph_context:
            return "❌ No relevant information found in the documents."

        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": f"""Business consultant.
                    RULES:
                    - Use ONLY the provided context
                    - Prefer GRAPH KNOWLEDGE over DOCUMENT CONTEXT
                    - If answer is missing, say "I don't know based on provided context"
                    """

                },
                {
                    "role": "user",
                    "content": f"DOCUMENT CONTEXT:\n{vector_context}\n\n"
                               f"GRAPH KNOWLEDGE:\n{graph_context}\n\n"
                               f"Question: {question}"
                }
            ]
        )

        return response.choices[0].message.content