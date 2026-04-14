import re
from typing import List, Dict
from src.services.text_chunker_service import TextChunkerService


class ChunkSearchService:

    """Keyword-based search over text chunks"""

    def __init__(self):
        self.chunks: List[Dict] = []
        self.index = {}

    def build(self, chunks: List[Dict]):
        self.chunks = chunks
        self._build_index()

    def _build_index(self):
        """Build keyword index (word -> chunk indices)"""
        self.index = {}

        for idx, chunk in enumerate(self.chunks):
            words = set(re.findall(r'\b\w+\b', chunk['text'].lower()))

            for word in words:
                if word not in self.index:
                    self.index[word] = []
                self.index[word].append(idx)

    def find_relevant(self, question: str, top_k: int = 3) -> List[Dict]:
        """Find most relevant chunks using keyword matching"""

        question_words = set(re.findall(r'\b\w+\b', question.lower()))

        stopwords = {
            'what', 'is', 'are', 'the', 'a', 'an', 'to', 'for', 'of',
            'and', 'or', 'in', 'on', 'at', 'by', 'with', 'without',
            'how', 'why', 'when', 'where', 'which'
        }

        keywords = question_words - stopwords

        if not keywords:
            return []

        chunk_scores = {}

        for keyword in keywords:
            if keyword in self.index:
                for chunk_idx in self.index[keyword]:
                    chunk_scores[chunk_idx] = chunk_scores.get(chunk_idx, 0) + 1

        scored_chunks = []

        for chunk_idx, score in sorted(
            chunk_scores.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if score > 0:
                chunk = self.chunks[chunk_idx].copy()
                chunk["score"] = score
                scored_chunks.append(chunk)

        return scored_chunks[:top_k]