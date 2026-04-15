import json
import asyncio
import aiohttp
from pathlib import Path

from src.core.config import Config
from src.services.text_chunker_service import TextChunkerService


class StableGraphRAG:
    def __init__(self):
        self.graph = {}
        self.root = Path(__file__).resolve().parents[1]

        self.model = "phi3"  # FAST model ONLY
        self.concurrency = 3  # 🔥 IMPORTANT: keep LOW

        self.counter = 0
        self.total = 0

    # -------------------------
    # MAIN
    # -------------------------
    async def build(self):
        print("🚀 STABLE GraphRAG START")

        text = self._load_documents()

        chunks = TextChunkerService().chunk_text(text)

        self.total = len(chunks)

        print(f"📦 chunks: {self.total}")

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

        print(f"📊 GRAPH NODES: {len(self.graph)}")

        self.save()

    # -------------------------
    # WORKER (KEY FIX)
    # -------------------------
    async def worker(self, session, queue):
        while True:
            chunk = await queue.get()

            try:
                triples = await self.call_llm(session, chunk)
                self.merge(triples)

            except Exception as e:
                print("ERR:", repr(e))

            self.counter += 1
            print(f"📈 {self.counter}/{self.total}")

            queue.task_done()

    # -------------------------
    # LLM CALL (SEQUENTIAL SAFE)
    # -------------------------
    async def call_llm(self, session, chunk):
        prompt = f"""
Return ONLY JSON array:
[
  {{"subject":"a","relation":"b","object":"c"}}
]

TEXT:
{chunk}
"""

        async with session.post(
            "http://127.0.0.1:11434/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            },
            timeout=120
        ) as resp:

            data = await resp.json()
            content = data["message"]["content"]

            return self.parse(content)

    # -------------------------
    # PARSER
    # -------------------------
    def parse(self, text):
        try:
            return json.loads(text)
        except:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start:end+1])
                except:
                    return []
        return []

    # -------------------------
    # MERGE
    # -------------------------
    def merge(self, triples):
        for t in triples:
            if not isinstance(t, dict):
                continue

            s = t.get("subject", "").lower()
            r = t.get("relation", "").lower()
            o = t.get("object", "").lower()

            if s and r and o:
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
    # SAVE
    # -------------------------
    def save(self):
        out = self.root / "data/graph/graph.json"
        out.parent.mkdir(parents=True, exist_ok=True)

        with open(out, "w") as f:
            json.dump(self.graph, f, indent=2)

        print("✅ saved")


if __name__ == "__main__":
    import asyncio

    asyncio.run(StableGraphRAG().build())
    print("DONE")