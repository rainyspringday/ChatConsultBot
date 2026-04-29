import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from src.api import analyze, auth, chat_sessions
from src.services.chroma_storage_service import ChromaStorageService
from src.services.rag_service import RAGService

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    chroma = ChromaStorageService()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    rag = RAGService(chroma,client)
    app.state.rag = rag



app.include_router(analyze.router)
app.include_router(auth.router)
app.include_router(chat_sessions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
