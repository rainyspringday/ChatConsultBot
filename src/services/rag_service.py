import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

from src.core.config import Config
from src.prompts.prompt_library import PromptLibrary
from src.core.guardrails import Guardrails
from src.services.intent_detection_service import IntentDetectionService


class RAGService:
    """
    Main RAG service responsible for:
    - intent detection
    - hybrid retrieval (vector + keyword)
    - graph-based context enrichment
    - guardrails (input + output)
    - prompt construction
    - LLM call orchestration
    """

    def __init__(self, chroma_reports, chroma_frameworks, client) -> None:
        self.chroma_reports = chroma_reports
        self.chroma_frameworks = chroma_frameworks
        self.client = client

        self.intent_detector = IntentDetectionService()
        self.guardrails = Guardrails()

        # Load graph and build index
        self.graph = self._load_graph()
        self.graph_index = self._build_graph_index()

        # Cache documents for keyword search
        self.reports_cache = self._get_all_documents(self.chroma_reports)
        self.frameworks_cache = self._get_all_documents(self.chroma_frameworks)

        # Infer document names (reports only)
        self.document_names_cache = self._infer_document_names()

    # -------------------------------------------------------------------------
    # GRAPH LOADING
    # -------------------------------------------------------------------------

    @staticmethod
    def _load_graph() -> List[Dict[str, str]]:
        """Load graph triplets from graph.json."""
        path = Config.graph_dir / "graph.json"
        if not path.exists():
            return []

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _build_graph_index(self) -> Dict[str, List[Dict[str, str]]]:
        """Build an inverted index for fast graph lookup."""
        index: Dict[str, List[Dict[str, str]]] = {}

        for triple in self.graph:
            subject = triple["subject"].lower()
            obj = triple["object"].lower()

            index.setdefault(subject, []).append(triple)
            index.setdefault(obj, []).append(triple)

        return index

    # -------------------------------------------------------------------------
    # GRAPH RETRIEVAL
    # -------------------------------------------------------------------------

    def _get_graph_context(self, query: str, max_results: int = 8) -> str:
        """Retrieve relevant graph triplets based on query terms."""
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

        # Direct term match
        for term in terms:
            if term in self.graph_index:
                for triple in self.graph_index[term]:
                    key = (triple["subject"], triple["relation"], triple["object"])
                    scored[key] = scored.get(key, 0) + 3

        # Fuzzy match
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

    # -------------------------------------------------------------------------
    # DOCUMENT LOADING
    # -------------------------------------------------------------------------

    def _get_all_documents(self, db, batch_size: int = 100) -> List[Dict[str, Any]]:
        """Load all documents from a Chroma collection."""
        collection = db.collection
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

    # -------------------------------------------------------------------------
    # SEARCH METHODS
    # -------------------------------------------------------------------------

    def _keyword_search(self, query: str, cache, k: int = 5) -> List[str]:
        """Simple keyword search over cached documents."""
        terms = query.lower().split()
        scored = []

        for doc in cache:
            text = doc["text"].lower()
            score = sum(t in text for t in terms)
            if score > 0:
                scored.append((score, doc["text"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:k]]

    def _vector_search(self, query: str, db) -> List[str]:
        """Vector search using Chroma."""
        res = db.search(query)
        if not res.get("documents"):
            return []
        return res["documents"][0]

    def _hybrid_search(self, query: str, k: int = 5, db=None) -> List[str]:
        """Hybrid search combining vector + keyword search."""
        db = db or self.chroma_reports

        cache = (
            self.frameworks_cache if db is self.chroma_frameworks
            else self.reports_cache
        )

        vector = self._vector_search(query, db)
        keyword = self._keyword_search(query, cache, k)

        seen = set()
        combined = []

        for doc in keyword + vector:
            if doc not in seen:
                seen.add(doc)
                combined.append(doc)

        return combined[:k]

    # -------------------------------------------------------------------------
    # DOCUMENT NAME INFERENCE
    # -------------------------------------------------------------------------

    def _infer_document_names(self) -> List[str]:
        """Infer document names from cleaned report files."""
        names = {
            file.name
            for file in Path(Config.output_dir).glob("*_cleaned.txt")
            if file.is_file()
        }

        if names:
            return sorted(names)

        # Fallback: extract names from document headers
        pattern = re.compile(r"---\s*(.+?)\s*---")
        for doc in self.reports_cache:
            text = doc.get("text", "")
            for match in pattern.findall(text):
                cleaned = match.strip()
                if cleaned:
                    names.add(cleaned)

        return sorted(names)

    # -------------------------------------------------------------------------
    # CONTEXT BUILDING
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_context(chunks: List[str], max_chunks: int = 3) -> str:
        """Join top chunks into a single context block."""
        filtered = [c.strip() for c in chunks if len(c.strip()) > 50]
        return "\n\n".join(filtered[:max_chunks])

    # -------------------------------------------------------------------------
    # RERANKING
    # -------------------------------------------------------------------------

    def _rerank(self, query: str, chunks: List[str], top_k: int = 3) -> List[str]:
        """Simple keyword-based reranking."""
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

    # -------------------------------------------------------------------------
    # RELEVANCE FILTER (Option A)
    # -------------------------------------------------------------------------

    def _is_relevant(self, chunks: List[str], question: str) -> bool:
        """Relevance filter used ONLY for framework + analysis queries."""
        q = question.lower()
        joined = " ".join(chunks).lower()

        # If the user query includes a whitelisted framework name, require that
        # at least one framework signal shows up in retrieved text. This avoids
        # false negatives on short prompts like "Explain SWOT".
        framework_signals = [k for k in self.intent_detector.allowed_frameworks if k and k in q]
        component_signals = [c for c in self.intent_detector.framework_components if c and c in q]

        # If the user is clearly asking about a whitelisted framework or one of its components,
        # require retrieval to contain at least a framework-level signal. Component terms can be
        # missing due to chunk boundaries; framework name match is sufficient.
        if framework_signals or component_signals:
            if any(fw in joined for fw in self.intent_detector.allowed_frameworks):
                return True
            # Otherwise fall back to stricter match against the specific signals present in query.
            required_terms = framework_signals + component_signals
            return any(term in joined for term in required_terms)

        # Competition → must retrieve Porter content
        if "competition" in q or "competitive" in q:
            return any(k in joined for k in [
                "porter", "five forces", "rivalry",
                "bargaining power", "substitutes", "industry structure"
            ])

        # Business model → must retrieve BMC or Lean Canvas
        if "business model" in q:
            return any(k in joined for k in [
                "business model canvas", "lean canvas",
                "value proposition", "customer segments"
            ])

        # Strategy → must retrieve Blue Ocean or Porter
        if "strategy" in q:
            return any(k in joined for k in [
                "blue ocean", "porter", "five forces", "strategic canvas"
            ])

        # Default: require at least one keyword overlap
        stop = {
            "explain", "describe", "define", "what", "is", "are", "the", "a", "an",
            "tell", "me", "about", "please", "in", "on", "of", "to", "and", "or",
            "for", "with"
        }
        terms = [w for w in re.findall(r"[a-z0-9]+", q) if w not in stop and len(w) > 2]
        return any(word in joined for word in terms)

    def _is_unknown_framework_query(self, question: str) -> bool:
        """
        Detect explicit requests for non-whitelisted frameworks.
        This is independent from intent routing, so unsupported framework
        prompts are rejected consistently.
        """
        q = question.lower()

        recommendation_requests = (
            "which framework" in q
            or "what framework should i use" in q
            or "choose a framework" in q
            or "recommend a framework" in q
            or "suggest framework" in q
        )
        if recommendation_requests:
            return False

        asks_to_explain = any(
            phrase in q for phrase in ("explain", "describe", "define", "what is", "tell me about")
        )
        framework_like = ("framework" in q) or ("matrix" in q)
        if not asks_to_explain or not framework_like:
            return False

        return not self.intent_detector.is_known_framework(q)

    @staticmethod
    def _is_report_query_relevant(chunks: List[str], question: str) -> bool:
        """
        Basic domain gate for REPORT queries to prevent out-of-domain answers.
        """
        q = question.lower()
        domain_terms = (
            "econom", "oecd", "imf", "world bank", "undp", "gdp", "inflation",
            "productivity", "growth", "policy", "development", "market", "business",
            "sales", "competition", "customer", "churn", "company", "revenue",
            "cost", "profit", "strategy", "report"
        )

        if not any(term in q for term in domain_terms):
            return False

        joined = " ".join(chunks).lower()
        query_words = [w for w in re.findall(r"[a-z0-9]+", q) if len(w) > 2]
        return any(word in joined for word in query_words)

    # -------------------------------------------------------------------------
    # MAIN PIPELINE
    # -------------------------------------------------------------------------

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

        normalized_question = safe_question.lower()

        # Prevent document inventory disclosure
        if (
            ("how many" in normalized_question or "count" in normalized_question)
            and ("document" in normalized_question or "file" in normalized_question)
        ):
            return "I cannot disclose indexed document inventory."

        # 2. INTENT ROUTING
        intent = self.intent_detector.detect(safe_question)

        # Reject unsupported frameworks even if intent was classified as REPORT.
        if self._is_unknown_framework_query(normalized_question):
            return "No framework detected in provided context."

        # For ANALYSIS queries, the user often asks "what framework should I use"
        # without naming one. That should be allowed. Only reject when the user is
        # explicitly asking to explain an unsupported framework.
        if intent == "FRAMEWORK":
            asked_to_explain = any(
                phrase in normalized_question
                for phrase in ("explain", "describe", "define", "what is", "tell me about")
            )
            if asked_to_explain and ("framework" in normalized_question or "matrix" in normalized_question):
                if not self.intent_detector.is_known_framework(normalized_question):
                    return "No framework detected in provided context."

        active_db = (
            self.chroma_frameworks if intent in ("FRAMEWORK", "ANALYSIS")
            else self.chroma_reports
        )

        # 3. RETRIEVAL
        chunks = self._hybrid_search(safe_question, k=10, db=active_db)
        chunks = self.guardrails.apply_context(chunks)

        if not chunks:
            return "I don't know based on provided context."

        # Relevance filtering ONLY for framework + analysis
        if intent in ("FRAMEWORK", "ANALYSIS"):
            if not self._is_relevant(chunks, safe_question):
                return "I don't know based on provided context."
        elif intent == "REPORT":
            if not self._is_report_query_relevant(chunks, safe_question):
                return "I don't know based on provided context."

        chunks = self._rerank(safe_question, chunks, top_k=3)
        context = self._build_context(chunks)
        graph_context = self._get_graph_context(safe_question)

        # 4. PROMPT CONSTRUCTION
        system_prompt = PromptLibrary.get(prompt_name)
        recent_history = (chat_history or [])[-4:]

        messages = self.guardrails.build_messages(
            question=safe_question,
            context=context,
            graph_context=graph_context,
            domain_system_prompt=system_prompt,
            chat_history=recent_history,
        )

        # 5. MODEL CALL
        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=messages,
        )

        raw_answer = response.choices[0].message.content or ""

        # 6. OUTPUT GUARDRAIL
        return self.guardrails.apply_output(raw_answer)

    # -------------------------------------------------------------------------
    # CHAT TITLE
    # -------------------------------------------------------------------------

    def generate_chat_title(self, first_message: str) -> str:
        """Generate a short chat title using the LLM."""
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
                    {"role": "user", "content": clean_message},
                ],
            )

            title = (response.choices[0].message.content or "").strip()
            if title:
                return title[:80]

        except Exception:
            pass

        fallback = " ".join(clean_message.split()[:6])
        return fallback[:80] if fallback else "New chat"
