import os
import json
import asyncio
import hashlib
from pathlib import Path
from typing import List, Dict

import spacy

from neo4j import GraphDatabase

from src.core.config import Config
from src.services.chroma_storage_service import ChromaStorageService


# -------------------------
# LOAD ENV
# -------------------------


NEO4J_URI = Config.NEO4J_URI        #
NEO4J_USERNAME = Config.NEO4J_USERNAME
NEO4J_PASSWORD = Config.NEO4J_PASSWORD


# -------------------------
# UTILS
# -------------------------

def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# -------------------------
# FAST EXTRACTOR
# -------------------------

class FastExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def extract(self, text: str) -> List[Dict[str, str]]:
        triples = []
        doc = self.nlp(text)
        ents = [ent.text for ent in doc.ents]

        for i in range(len(ents) - 1):
            triples.append({
                "subject": ents[i],
                "relation": "RELATED_TO",
                "object": ents[i + 1]
            })

        return triples


# -------------------------
# MAIN GRAPH BUILDER
# -------------------------

class Graph:
    def __init__(self):
        self.extractor = FastExtractor()
        self.chroma = ChromaStorageService()
        self.triples = []
        self.driver = None  # <-- IMPORTANT: no connection yet

    # ---------------------------------------------------------
    # STEP 1 — BUILD TRIPLES (NO NEO4J CONNECTION)
    # ---------------------------------------------------------
    async def build_triples(self):
        print("🚀 Extracting triples...")

        results = self.chroma.collection.get(include=["documents"])
        chunks = results["documents"]

        for i, text in enumerate(chunks):
            extracted = self.extractor.extract(text)
            self.triples.extend(extracted)

            if (i + 1) % 10 == 0:
                print(f"⚙️ Extracted: {i+1}/{len(chunks)}")

        print(f"📊 Total triples extracted: {len(self.triples)}")
        self.save()

    # ---------------------------------------------------------
    # SAVE TRIPLES LOCALLY
    # ---------------------------------------------------------
    def save(self):
        save_path = f"{Config.graph_dir}/graph.json"
        Path(save_path).write_text(json.dumps(self.triples, indent=2), encoding="utf-8")
        print(f"💾 Saved triples → {save_path}")

    # ---------------------------------------------------------
    # STEP 2 — CONNECT TO NEO4J (ONLY WHEN CALLED)
    # ---------------------------------------------------------
    def connect(self):
        print("🔌 Connecting to Neo4j...")

        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            print("🟢 Connected to Neo4j")
        except Exception as e:
            print("🔴 Neo4j connection FAILED")
            print(e)
            raise

    # ---------------------------------------------------------
    # STEP 3 — UPLOAD TRIPLES (ONLY WHEN CALLED)
    # ---------------------------------------------------------
    def upload(self, batch_size=1000):
        if not self.driver:
            raise RuntimeError("Call connect() before upload()")

        print("📡 Uploading triples to Neo4j...")

        query = """
        UNWIND $rows AS t
        MERGE (s:Entity {name: t.subject})
        MERGE (o:Entity {name: t.object})
        MERGE (s)-[:RELATED_TO]->(o)
        """

        with self.driver.session() as session:
            for i in range(0, len(self.triples), batch_size):
                batch = self.triples[i:i + batch_size]

                session.execute_write(lambda tx: tx.run(query, rows=batch))

                print(f"   ✅ Uploaded batch {i//batch_size + 1} ({len(batch)} triples)")

        print("🎉 Upload complete!")


# -------------------------
# RUN (EXAMPLE)
# -------------------------

if __name__ == "__main__":
    g = Graph()
    asyncio.run(g.build_triples())
