import os
from pathlib import Path
from groq import Groq
from langchain_classic.chains.question_answering.map_reduce_prompt import messages

from src.prompts.prompt_library import PromptLibrary
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

    def ask(self, question: str, prompt_name:str| None = None) -> str:
        """Main RAG pipeline"""

        relevant_chunks = self.search.find_relevant(question)
        graph_context = self.get_graph_context(question)
        vector_context = "\n\n".join(chunk["text"] for chunk in relevant_chunks)
        system_prompt=PromptLibrary.get(prompt_name)


        groq_messages=[]

        if isinstance(system_prompt, str) and system_prompt.strip():
            groq_messages.append({
                "role": "system",
                "content": system_prompt
            })

        groq_messages.append({
            "role": "user",
            "content": (
                f"DOCUMENT CONTEXT:\n{vector_context}\n\n"
                f"GRAPH KNOWLEDGE:\n{graph_context}\n\n"
                f"Question: {question}"
            )
        })
        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=groq_messages
        )

        return response.choices[0].message.content

    def generate_chat_title(self, first_message: str) -> str:
        """Create a short chat title from first user message."""
        clean_message = first_message.strip()
        if not clean_message:
            return "New chat"

        try:
            response = self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You create very short chat titles. Return only one title, "
                            "max 6 words, no quotes, no punctuation at the end."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Create a title for this message:\n{clean_message}",
                    },
                ],
            )
            title = (response.choices[0].message.content or "").strip()
            if title:
                return title[:80]
        except Exception:
            pass

        fallback = " ".join(clean_message.split()[:6]).strip()
        return fallback[:80] if fallback else "New chat"