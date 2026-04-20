from fastapi import FastAPI, HTTPException, Depends, APIRouter
from pydantic import BaseModel
from src.api.deps import get_rag
from src.api.auth import get_current_user
from src.services.rag_service import RAGService

router=APIRouter()


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=AnswerResponse)
def ask_question(
    request: QuestionRequest,
    rag: RAGService = Depends(get_rag),
    username: str = Depends(get_current_user),
):

    try:
        response = rag.ask(request.question,"chat")
        return AnswerResponse(answer=response.strip())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

