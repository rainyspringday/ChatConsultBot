from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.rag_system import FastRAG
import uvicorn

rag = FastRAG()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str


@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    try:
        # Get response from RAG
        response = rag.ask(request.question)

        # Return in format your frontend expects: { answer: "..." }
        return AnswerResponse(answer=response.strip())

    except Exception as e:
        # Your frontend handles this error format
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)