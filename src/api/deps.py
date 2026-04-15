from fastapi import Request
from src.services.rag_service import RAGService


def get_rag(request: Request) -> RAGService:
    return request.app.state.rag