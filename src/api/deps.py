from src.services.RAGService import RAGService
from src.services.TextChunkerService import TextChunkerService
from src.services.ChunkSearchService import ChunkSearchService


def get_rag():
    return RAGService(
        chunker=TextChunkerService(),
        search=ChunkSearchService()
    )