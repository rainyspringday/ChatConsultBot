import json
import os
from typing import List, Dict, Any

from groq import Groq
from src.core.config import Config
from src.prompts.prompt_library import PromptLibrary


class RAGService:
    def __init__(self, chroma) -> None:
        self.chroma = chroma
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        self.graph = self._load_graph()
        self.all_docs_cache = self._get_all_documents()

    def _load_graph(self) -> List[Dict[str, str]]:
        graph_path = Config.graph_dir / "graph.json"
        with graph_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _get_all_documents(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        collection = self.chroma.collection
        results: List[Dict[str, Any]] = []

        offset = 0
        while True:
            batch = collection.get(limit=batch_size, offset=offset)

            documents = batch.get("documents", [])
            metadatas = batch.get("metadatas", [])

            if not documents:
                break

            for doc, meta in zip(documents, metadatas):
                results.append({
                    "text": doc,
                    "metadata": meta,
                })

            offset += batch_size

        return results

    def _keyword_search(self, query: str, k: int = 5) -> List[str]:
        query_terms = query.lower().split()
        scored_results = []

        for doc in self.all_docs_cache:
            text = doc["text"].lower()
            score = sum(term in text for term in query_terms)

            if score > 0:
                scored_results.append((score, doc["text"]))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_results[:k]]

    def _vector_search(self, query: str) -> List[str]:
        results = self.chroma.search(query)

        if not results.get("documents"):
            return []

        documents = results["documents"]
        if not documents or not documents[0]:
            return []

        return documents[0]

    def _hybrid_search(self, query: str, k: int = 5) -> List[str]:
        keyword_docs = self._keyword_search(query, k)
        vector_docs = self._vector_search(query)

        combined: List[str] = []
        seen = set()

        for doc in keyword_docs + vector_docs:
            if doc not in seen:
                seen.add(doc)
                combined.append(doc)

        return combined[:k]

    def _get_graph_context(self, query: str) -> str:
        query_terms = query.lower().split()
        matches = []

        for triple in self.graph:
            subject = triple["subject"].lower()
            relation = triple["relation"].lower()
            obj = triple["object"].lower()

            if any(term in subject or term in relation or term in obj for term in query_terms):
                matches.append(
                    f"{triple['subject']} -[{triple['relation']}]-> {triple['object']}"
                )

        return "\n".join(matches)

    @staticmethod
    def _build_context(chunks: List[str], max_chunks: int = 3) -> str:
        filtered = [c.strip() for c in chunks if len(c.strip()) > 50]
        return "\n\n".join(filtered[:max_chunks])

    def ask(self, question: str, prompt_name: str | None = None) -> str:
        chunks = self._hybrid_search(question, k=8)

        if not chunks:
            return "No relevant context found."

        context = self._build_context(chunks)
        graph_context = self._get_graph_context(question)

        system_prompt = PromptLibrary.get(prompt_name)

        messages = []

        if isinstance(system_prompt, str) and system_prompt.strip():
            messages.append({
                "role": "system",
                "content": system_prompt,
            })

        messages.append({
            "role": "user",
            "content": (
                f"DOCUMENT CONTEXT:\n{context}\n\n"
                f"GRAPH KNOWLEDGE:\n{graph_context}\n\n"
                f"Question: {question}"
            ),
        })

        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=messages,
        )

        return response.choices[0].message.content or ""

    def generate_chat_title(self, first_message: str) -> str:
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
                            "Create a short chat title (max 6 words). "
                            "No quotes. No trailing punctuation."
                        ),
                    },
                    {
                        "role": "user",
                        "content": clean_message,
                    },
                ],
            )

            title = (response.choices[0].message.content or "").strip()
            if title:
                return title[:80]

        except Exception:
            pass

        fallback = " ".join(clean_message.split()[:6])
        return fallback[:80] if fallback else "New chat"