from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import chat, analyze
from src.services.chunk_search_service import ChunkSearchService
from src.services.rag_service import RAGService
from src.services.text_chunker_service import TextChunkerService

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = None

@app.on_event("startup")
def startup():
    global rag
    rag = RAGService(
        chunker=TextChunkerService(),
        search=ChunkSearchService(),
    )
    rag.build()



app.include_router(chat.router)
app.include_router(analyze.router)


@app.get("/health")
def health():
    return {"status": "ok"}
