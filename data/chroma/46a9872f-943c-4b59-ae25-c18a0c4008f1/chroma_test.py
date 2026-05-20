import chromadb

from src.core.config import Config

client = chromadb.PersistentClient(path=Config.chroma_dir)


collection = client.get_collection("chunks")
items = collection.get(include=["embeddings", "documents", "metadatas"])

print(items)
