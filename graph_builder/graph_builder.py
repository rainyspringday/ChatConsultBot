import json
import asyncio
import aiohttp
from pathlib import Path

from src.core.config import Config
from src.services.text_chunker_service import TextChunkerService


class GraphRAG:
    def __init__(self):
        self.graph = {}

        # -------------------------
        # FIXED ROOT (PROJECT ROOT)
        # -------------------------
        self.root = Path(__file__).resolve()

        # go up until we find "data" folder (project root detection)
        while not (self.root / "data").exists():
            self.root = self.root.parent

        print(f"📁 Project root resolved: {self.root}")

        self.model = "phi3"
        self.concurrency = 3

        self.counter = 0
        self.total = 0

    # -------------------------
    # MAIN
    # -------------------------
    async def build(self):
        print("🚀 GraphRAG START")

        text = self._load_documents()

        chunks = TextChunkerService().chunk_text(text)
        self.total = len(chunks)

        print(f"📦 Total chunks: {self.total}")

        queue = asyncio.Queue()

        for c in chunks:
            queue.put_nowait(c["text"][:700])

        async with aiohttp.ClientSession() as session:

            workers = [
                asyncio.create_task(self.worker(session, queue))
                for _ in range(self.concurrency)
            ]

            await queue.join()

            for w in workers:
                w.cancel()

        print(f"📊 FINAL GRAPH NODES: {len(self.graph)}")

        self.save()

    # -------------------------
    # WORKER
    # -------------------------
    async def worker(self, session, queue):
        while True:
            chunk = await queue.get()

            try:
                triples = await self.call_llm(session, chunk)
                self.merge(triples)

            except Exception as e:
                print("❌ ERROR:", repr(e))

            self.counter += 1
            print(f"📈 {self.counter}/{self.total}")

            queue.task_done()

    # -------------------------
    # LLM CALL
    # -------------------------
    async def call_llm(self, session, chunk):
        prompt = f"""
Extract ONLY JSON triples:

[
  {{"subject":"a","relation":"b","object":"c"}}
]

TEXT:
{chunk}
"""

        async with session.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        ) as resp:

            data = await resp.json()
            text = data.get("response", "")

            return self.parse(text)

    # -------------------------
    # PARSER
    # -------------------------
    @staticmethod
    def parse(text):
        if not text:
            return []

        try:
            return json.loads(text)
        except:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end + 1])
                except:
                    return []
        return []

    # -------------------------
    # MERGE (SAFE)
    # -------------------------
    def merge(self, triples):
        for t in triples:
            if not isinstance(t, dict):
                continue

            s = t.get("subject")
            r = t.get("relation")
            o = t.get("object")

            # SAFEGUARD (prevents crashes)
            if not s or not r or not o:
                continue

            s = str(s).strip().lower()
            r = str(r).strip().lower()
            o = str(o).strip().lower()

            self.graph.setdefault(s, []).append((r, o))

    # -------------------------
    # LOAD
    # -------------------------
    def _load_documents(self):
        folder = self.root / Config.output_dir

        return "\n\n".join(
            f.read_text(encoding="utf-8")
            for f in folder.glob("*_cleaned.txt")
        )

    # -------------------------
    # SAVE (FIXED PATH)
    # -------------------------
    def save(self):
        out = self.root / "data/graph/graph.json"
        out.parent.mkdir(parents=True, exist_ok=True)

        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.graph, f, indent=2)

        print(f"✅ Saved graph → {out.resolve()}")
