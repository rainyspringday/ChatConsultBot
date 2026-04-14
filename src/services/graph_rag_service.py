import os
from pathlib import Path
from groq import Groq

from src.core.config import Config
class GraphRagService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.graph = {}

    def build(self, chunks):
        for chunk in chunks:
            triples = self._extract_triples(chunk["text"])

            for t in triples:
                subj = t["subject"].lower()
                rel = t["relation"]
                obj = t["object"].lower()

                if subj not in self.graph:
                    self.graph[subj] = []

                self.graph[subj].append((rel, obj))

    def get_context(self, query: str) -> str:
        entities = self._extract_entities(query)

        facts = []
        for e in entities:
            if e in self.graph:
                for rel, obj in self.graph[e]:
                    facts.append(f"{e} {rel} {obj}")

        return "\n".join(facts)

    def _extract_entities(self, query):
        return [w.lower() for w in query.split()]

    def _extract_triples(self, text):
        prompt = f"""
        
        Extract up to 15 high-quality, non-redundant triplets.
        Rules:
        - Only include meaningful, informative relationships
        - Prefer cause-effect, impact, or functional relations
        - Avoid vague relations like "is", "has", "was"
        - Avoid duplicates or paraphrases
        - If fewer than 15 high-quality triplets exist, return fewer
        
        Extract relationships as JSON:
        [
          {{"subject": "...", "relation": "...", "object": "..."}}
        ]
        Return ONLY valid JSON.
        No explanations.
        No markdown.
        No text outside JSON.

        Text:
        {text}
        """

        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )

        import json
        return json.loads(response.choices[0].message.content)