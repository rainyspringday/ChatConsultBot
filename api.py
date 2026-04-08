from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import Config
from src.rag_system import FastRAG


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


class AnalyzeRequest(BaseModel):
    companyName: str


class AnalyzeResponse(BaseModel):
    companyName: str
    currentState: list[str]
    todoPlan: list[str]


app = FastAPI(title="ChatConsultBot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = FastRAG()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not Config.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    try:
        answer = rag.ask(question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {exc}") from exc

    return AskResponse(answer=answer)


@app.post("/analyze-company", response_model=AnalyzeResponse)
def analyze_company(payload: AnalyzeRequest) -> AnalyzeResponse:
    company_name = payload.companyName.strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name cannot be empty.")

    return AnalyzeResponse(
        companyName=company_name,
        currentState=[
            "API integration for company analysis is in progress.",
            "Automated process diagnostics are not enabled yet.",
            "Real company data mapping will be added in backend phase 2.",
        ],
        todoPlan=[
            "Connect data sources and normalize KPI schema.",
            "Run baseline process analysis with operational metrics.",
            "Generate prioritized 30/60/90-day execution roadmap.",
            "Track improvements with recurring monthly reviews.",
        ],
    )
