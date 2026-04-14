from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import chat, analyze

app = FastAPI()

# Middleware first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat.router)
app.include_router(analyze.router)


@app.get("/health")
def health():
    return {"status": "ok"}
