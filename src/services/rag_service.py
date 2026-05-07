import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

from src.core.config import Config
from src.prompts.prompt_library import PromptLibrary
from src.core.guardrails import Guardrails


class RAGService:
    def __init__(self, chroma, client) -> None:
        self.chroma = chroma
        self.client = client

        # unified guardrails service
        self.guardrails = Guardrails()

        # your improved logic
        self.graph = self._load_graph()
        self.graph_index = self._build_graph_index()

        self.all_docs_cache = self._get_all_documents()
        self.document_names_cache = self._infer_document_names()

    # ---------------------------
    # GRAPH LOADING
    # ---------------------------

    @staticmethod
    def _load_graph() -> List[Dict[str, str]]:
        path = Config.graph_dir / "graph.json"
        if not path.exists():
            return []

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        return data if isinstance(data, list) else []

    def _build_graph_index(self) -> Dict[str, List[Dict[str, str]]]:
        index: Dict[str, List[Dict[str, str]]] = {}

        for triple in self.graph:
            subject = triple["subject"].lower()
            obj = triple["object"].lower()

            index.setdefault(subject, []).append(triple)
            index.setdefault(obj, []).append(triple)

        return index

    # ---------------------------
    # GRAPH RETRIEVAL
    # ---------------------------

    def _get_graph_context(self, query: str, max_results: int = 8) -> str:
        STOPWORDS = {
            "what", "is", "a", "an", "the", "how", "why",
            "do", "does", "of", "in", "on", "for", "to", "and"
        }

        terms = [
            t for t in query.lower().split()
            if t not in STOPWORDS and len(t) > 1
        ]

        if not terms:
            return ""

        scored: Dict[Tuple[str, str, str], int] = {}

        for term in terms:
            if term in self.graph_index:
                for triple in self.graph_index[term]:
                    key = (triple["subject"], triple["relation"], triple["object"])
                    scored[key] = scored.get(key, 0) + 3

        for triple in self.graph:
            text = f"{triple['subject']} {triple['relation']} {triple['object']}".lower()
            for term in terms:
                if term in text:
                    key = (triple["subject"], triple["relation"], triple["object"])
                    scored[key] = scored.get(key, 0) + 1

        ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
        top = ranked[:max_results]

        return "\n".join(
            f"{s} -[{r}]-> {o}"
            for ((s, r, o), _) in top
        )

    # ---------------------------
    # VECTOR + KEYWORD SEARCH
    # ---------------------------

    def _get_all_documents(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        collection = self.chroma.collection
        results = []

        offset = 0
        while True:
            batch = collection.get(limit=batch_size, offset=offset)

            docs = batch.get("documents", [])
            metas = batch.get("metadatas", [])

            if not docs:
                break

            for d, m in zip(docs, metas):
                results.append({"text": d, "metadata": m})

            offset += batch_size

        return results

    def _keyword_search(self, query: str, k: int = 5) -> List[str]:
        terms = query.lower().split()
        scored = []

        for doc in self.all_docs_cache:
            text = doc["text"].lower()
            score = sum(t in text for t in terms)

            if score > 0:
                scored.append((score, doc["text"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:k]]

    def _infer_document_names(self) -> List[str]:
        names = {
            file.name
            for file in Path(Config.output_dir).glob("*_cleaned.txt")
            if file.is_file()
        }
        if names:
            return sorted(names)

        pattern = re.compile(r"---\s*(.+?)\s*---")
        for doc in self.all_docs_cache:
            text = doc.get("text", "")
            for match in pattern.findall(text):
                cleaned = match.strip()
                if cleaned:
                    names.add(cleaned)
        return sorted(names)

    def _vector_search(self, query: str) -> List[str]:
        res = self.chroma.search(query)
        if not res.get("documents"):
            return []
        return res["documents"][0]

    def _hybrid_search(self, query: str, k: int = 5) -> List[str]:
        vector = self._vector_search(query)
        keyword = self._keyword_search(query, k)

        seen = set()
        combined = []

        for doc in keyword + vector:
            if doc not in seen:
                seen.add(doc)
                combined.append(doc)

        return combined[:k]

    # ---------------------------
    # CONTEXT BUILDING
    # ---------------------------

    @staticmethod
    def _build_context(chunks: List[str], max_chunks: int = 3) -> str:
        filtered = [c.strip() for c in chunks if len(c.strip()) > 50]
        return "\n\n".join(filtered[:max_chunks])

    # ---------------------------
    # RERANKING
    # ---------------------------

    def _rerank(self, query: str, chunks: List[str], top_k: int = 3) -> List[str]:
        if not chunks:
            return []

        query_terms = set(query.lower().split())
        scored = []

        for chunk in chunks:
            text = chunk.lower()
            keyword_score = sum(term in text for term in query_terms)
            position_score = sum(text.find(term) != -1 for term in query_terms)
            score = keyword_score + 0.5 * position_score
            scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    # ---------------------------
    # MAIN PIPELINE
    # ---------------------------

    def ask(
        self,
        question: str,
        prompt_name: str | None = None,
        chat_history: List[Dict[str, str]] | None = None,
    ) -> str:

        # 1. INPUT GUARDRAIL
        safe_question = self.guardrails.apply_input(question)
        if safe_question == "INVALID_QUERY":
            return "I cannot help with that request."

        # special case: "how many documents"
        normalized_question = safe_question.lower()
        if (
            ("how many" in normalized_question or "count" in normalized_question)
            and ("document" in normalized_question or "file" in normalized_question)
        ):
            return "I cannot disclose indexed document inventory."

        # 2. RETRIEVAL
        chunks = self._hybrid_search(safe_question, k=10)
        chunks = self.guardrails.apply_context(chunks)

        if not chunks:
            return "No relevant context found."

        chunks = self._rerank(safe_question, chunks, top_k=3)
        context = self._build_context(chunks)
        graph_context = self._get_graph_context(safe_question)

        # 3. PROMPTS
        system_prompt = PromptLibrary.get(prompt_name)
        recent_history = (chat_history or [])[-4:]

        messages = self.guardrails.build_messages(
            question=safe_question,
            context=context,
            graph_context=graph_context,
            domain_system_prompt=system_prompt,
            chat_history=recent_history,
        )

        # 4. MODEL CALL
        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=messages,
        )

        raw_answer = response.choices[0].message.content or ""

        # 5. OUTPUT GUARDRAIL
        return self.guardrails.apply_output(raw_answer)

    # ---------------------------
    # CHAT TITLE
    # ---------------------------

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
