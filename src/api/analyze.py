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
    company = request.companyName

    # 1. Guardrail check for current state
    current_state_response = rag.ask(company, "analyze-state")
    if current_state_response == "INVALID_QUERY":
        return CompanyAnalysisResponse(
            companyName=company,
            currentState=["Invalid or unsafe query."],
            todoPlan=["Invalid or unsafe query."]
        )
    # 2. Parse current state
    current_state_points = [
        point.strip("- •").strip()
        for point in current_state_response.split("\n")
        if point.strip() and point.strip()[0] in "-•"
    ]
    if not current_state_points:
        current_state_points = [
            sentence.strip()
            for sentence in current_state_response.split(". ")
            if sentence.strip()
        ][:6]

    # 3. Guardrail check for todo plan
    todo_response = rag.ask(company, "analyze_plan")
    if todo_response == "INVALID_QUERY":
        return CompanyAnalysisResponse(
            companyName=company,
            currentState=current_state_points[:6],
            todoPlan=["Invalid or unsafe query."]
        )

    # 4. Parse todo plan
    todo_points = [
        point.strip("- •").strip()
        for point in todo_response.split("\n")
        if point.strip() and point.strip()[0] in "-•"
    ]
    if not todo_points:
        todo_points = [
            sentence.strip()
            for sentence in todo_response.split(". ")
            if sentence.strip()
        ][:6]

    final_current_state = current_state_points[:6]
    final_todo = todo_points[:6]

    # 5. Save to DB
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

