from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.rag_system import FastRAG
import uvicorn
from typing import List, Dict
from pydantic import BaseModel
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
        return AnswerResponse(answer=response.strip())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "ok"}


class CompanyAnalysisRequest(BaseModel):
    companyName: str


class CompanyAnalysisResponse(BaseModel):
    companyName: str
    currentState: List[str]
    todoPlan: List[str]


@app.post("/analyze-company", response_model=CompanyAnalysisResponse)
def analyze_company(request: CompanyAnalysisRequest):
    """
    Analyze a company and return current state and todo plan using RAG
    """
    try:
        company = request.companyName

        # Query RAG for company analysis
        # Current State Analysis
        current_state_prompt = f"""
        Based on the available documents about {company}, provide a detailed analysis of their CURRENT STATE including:
        1. Business operations status
        2. Financial health indicators
        3. Market position
        4. Key challenges
        5. Strengths and weaknesses

        Format as 5-7 bullet points.
        """

        current_state_response = rag.ask(current_state_prompt)
        current_state_points = [
            point.strip("- •").strip()
            for point in current_state_response.split("\n")
            if point.strip() and point.strip()[0] in "-•"
        ]

        # If no bullet points found, split by sentences
        if not current_state_points:
            current_state_points = [
                sentence.strip()
                for sentence in current_state_response.split(". ")
                if sentence.strip()
            ][:6]

        # TODO Plan Generation
        todo_plan_prompt = f"""
        Based on the analysis of {company}, create a prioritized 30/60/90-day action plan including:
        1. Immediate fixes (next 30 days)
        2. Strategic improvements (60 days)
        3. Long-term initiatives (90 days)

        Provide 5-7 specific, actionable recommendations.
        """

        todo_response = rag.ask(todo_plan_prompt)
        todo_points = [
            point.strip("- •").strip()
            for point in todo_response.split("\n")
            if point.strip() and point.strip()[0] in "-•"
        ]

        # If no bullet points found, split by numbers or sentences
        if not todo_points:
            todo_points = [
                sentence.strip()
                for sentence in todo_response.split(". ")
                if sentence.strip()
            ][:6]

        return CompanyAnalysisResponse(
            companyName=company,
            currentState=current_state_points[:6],  # Limit to 6 points
            todoPlan=todo_points[:6]  # Limit to 6 points
        )

    except Exception as e:
        return CompanyAnalysisResponse(
            companyName=request.companyName,
            currentState=[
                f"Analysis in progress: {str(e)[:100]}",
                "RAG system is processing available documents",
                "Check if company documents are uploaded",
                "Try again with more specific company information"
            ],
            todoPlan=[
                "Ensure company documents are loaded into RAG system",
                "Verify document quality and relevance",
                "Run specific queries for better results",
                "Consider uploading additional company data"
            ]
        )



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)