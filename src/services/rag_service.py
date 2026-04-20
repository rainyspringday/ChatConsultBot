import json
import os

from groq import Groq
from src.core.config import Config
from src.prompts.prompt_library import PromptLibrary


class RAGService:
    def __init__(self, chroma):

        self.chroma = chroma
        self.text = ""
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        graph_path = Config.graph_dir / "graph.json"
        with graph_path.open("r", encoding="utf-8") as f:
            self.graph = json.load(f)


    def get_graph_context(self, query: str) -> str:
        query = query.lower()

        nodes = self.graph.get("nodes", [])

        return "\n".join(
            n["text"]
            for n in nodes
            if query in n["text"].lower()
        )

    def ask(self, question: str, prompt_name:str| None = None) -> str:
        """Main RAG pipeline"""

        docs=self.chroma.search(question)
        if not docs["documents"] or not docs["documents"][0]:
            return "No relevant documents found."


        relevant_chunks = docs["documents"][0]  # list of strings

        vector_context = "\n\n".join(relevant_chunks)
        
        graph_context = self.get_graph_context(question)
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