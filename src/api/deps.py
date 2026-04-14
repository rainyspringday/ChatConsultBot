from src.services.rag_service import RAGService
from src.services.text_chunker_service import TextChunkerService
from src.services.chunk_search_service import ChunkSearchService


def get_rag():
    return RAGService(
        chunker=TextChunkerService(),
        search=ChunkSearchService()
    )