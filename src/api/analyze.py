import json
from typing import List
from fastapi import Depends, APIRouter
from pydantic import BaseModel
from src.api.deps import get_rag
from src.api.auth import get_current_user
from src.core.db import get_connection, init_db
from src.services.rag_service import RAGService

router=APIRouter()
init_db()

class CompanyAnalysisRequest(BaseModel):
    companyName: str


class CompanyAnalysisResponse(BaseModel):
    id: int | None = None
    companyName: str
    currentState: List[str]
    todoPlan: List[str]
    createdAt: str | None = None


@router.get("/company-analyses", response_model=List[CompanyAnalysisResponse])
def list_company_analyses(username: str = Depends(get_current_user)):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, company_name, current_state_json, todo_plan_json, created_at
            FROM company_analyses
            WHERE username = ?
            ORDER BY id DESC
            """,
            (username,),
        ).fetchall()
    return [
        CompanyAnalysisResponse(
            id=row["id"],
            companyName=row["company_name"],
            currentState=json.loads(row["current_state_json"]),
            todoPlan=json.loads(row["todo_plan_json"]),
            createdAt=row["created_at"],
        )
        for row in rows
    ]


@router.post("/analyze-company", response_model=CompanyAnalysisResponse)
def analyze_company(
    request: CompanyAnalysisRequest,
    rag: RAGService = Depends(get_rag),
    username: str = Depends(get_current_user),
):
    """
    Analyze a company and return current state and  plan for using RAG
    """
    try:
        company = request.companyName



        current_state_response = rag.ask(company,"analyze-state")
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



        todo_response = rag.ask(company,"analyze_plan")
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

        final_current_state = current_state_points[:6]
        final_todo = todo_points[:6]
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO company_analyses (
                    username, company_name, current_state_json, todo_plan_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    username,
                    company,
                    json.dumps(final_current_state, ensure_ascii=False),
                    json.dumps(final_todo, ensure_ascii=False),
                ),
            )
            analysis_id = cursor.lastrowid
            row = conn.execute(
                "SELECT created_at FROM company_analyses WHERE id = ?",
                (analysis_id,),
            ).fetchone()
            conn.commit()

        return CompanyAnalysisResponse(
            id=analysis_id,
            companyName=company,
            currentState=final_current_state,
            todoPlan=final_todo,
            createdAt=row["created_at"],
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

