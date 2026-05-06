import json
import re
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.auth import get_current_user
from src.api.deps import get_rag
from src.core.db import get_connection, init_db
from src.services.rag_service import RAGService

router = APIRouter()
init_db()


def _normalize_item(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^[\-*•\s]+", "", cleaned)
    cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
    cleaned = cleaned.replace("**", "").strip()
    return cleaned


def _extract_points(raw_text: str, max_points: int = 10) -> List[str]:
    if raw_text.strip().startswith("{"):
        return []

    points: List[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^([\-*•]|\d+[\.\)])\s+", stripped):
            normalized = _normalize_item(stripped)
            if normalized and not normalized.endswith(":"):
                points.append(normalized)

    if not points:
        sentence_chunks = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", raw_text.strip())
        for chunk in sentence_chunks:
            normalized = _normalize_item(chunk)
            if normalized and not normalized.endswith(":"):
                points.append(normalized)

    unique_points: List[str] = []
    seen = set()
    for point in points:
        key = point.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_points.append(point)
        if len(unique_points) >= max_points:
            break

    return unique_points


class CompanyAnalysisRequest(BaseModel):
    companyName: str


class RevenuePoint(BaseModel):
    year: int
    revenue: float
    expectedRevenue: float


class CompanyAnalysisResponse(BaseModel):
    id: int | None = None
    companyName: str
    currentState: List[str]
    todoPlan: List[str]
    benchmarkCompany: str | None = None
    maturityScore: int | None = None
    focusTopics: List[str] = []
    revenueSeries: List[RevenuePoint] = []
    userRating: int | None = None
    createdAt: str | None = None


class CompanyAnalysisRatingRequest(BaseModel):
    rating: int = Field(..., ge=0, le=5)


def _parse_metrics(raw_text: str) -> tuple[int | None, List[str], List[RevenuePoint]]:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*?\}", raw_text)
        if not match:
            return None, [], []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None, [], []

    score = data.get("maturityScore")
    if not isinstance(score, int):
        score = None

    raw_topics = data.get("focusTopics", [])
    topics = [str(topic).strip() for topic in raw_topics if str(topic).strip()][:6]

    series: List[RevenuePoint] = []
    for point in data.get("revenueSeries", [])[:8]:
        try:
            year = int(point.get("year"))
            revenue = float(point.get("revenue"))
            expected = float(point.get("expectedRevenue"))
        except (TypeError, ValueError, AttributeError):
            continue
        if revenue <= 0 or expected <= 0:
            continue
        series.append(
            RevenuePoint(year=year, revenue=revenue, expectedRevenue=expected)
        )

    return score, topics, series


@router.get("/company-analyses", response_model=List[CompanyAnalysisResponse])
def list_company_analyses(username: str = Depends(get_current_user)):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                company_name,
                current_state_json,
                todo_plan_json,
                benchmark_company,
                maturity_score,
                focus_topics_json,
                revenue_series_json,
                user_rating,
                created_at
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
            benchmarkCompany=row["benchmark_company"],
            maturityScore=row["maturity_score"],
            focusTopics=json.loads(row["focus_topics_json"])
            if row["focus_topics_json"]
            else [],
            revenueSeries=json.loads(row["revenue_series_json"])
            if row["revenue_series_json"]
            else [],
            userRating=row["user_rating"],
            createdAt=row["created_at"],
        )
        for row in rows
    ]


@router.delete("/company-analyses/{analysis_id}")
def delete_company_analysis(analysis_id: int, username: str = Depends(get_current_user)):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM company_analyses WHERE id = ? AND username = ?",
            (analysis_id, username),
        ).fetchone()
        if not row:
            return {"status": "not_found", "analysisId": analysis_id}
        conn.execute(
            "DELETE FROM company_analyses WHERE id = ? AND username = ?",
            (analysis_id, username),
        )
        conn.commit()
    return {"status": "deleted", "analysisId": analysis_id}


@router.post("/company-analyses/{analysis_id}/rating")
def rate_company_analysis(
    analysis_id: int,
    payload: CompanyAnalysisRatingRequest,
    username: str = Depends(get_current_user),
):
    rating = int(payload.rating)
    if rating < 0 or rating > 5:
        return {"status": "invalid_rating", "analysisId": analysis_id}

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM company_analyses WHERE id = ? AND username = ?",
            (analysis_id, username),
        ).fetchone()
        if not row:
            return {"status": "not_found", "analysisId": analysis_id}
        conn.execute(
            "UPDATE company_analyses SET user_rating = ? WHERE id = ? AND username = ?",
            (rating, analysis_id, username),
        )
        conn.commit()
    return {"status": "saved", "analysisId": analysis_id, "rating": rating}


@router.post("/analyze-company", response_model=CompanyAnalysisResponse)
def analyze_company(
    request: CompanyAnalysisRequest,
    rag: RAGService = Depends(get_rag),
    username: str = Depends(get_current_user),
):
    try:
        company = request.companyName.strip()
        normalized = company.lower()
        leaders = {"microsoft", "google", "apple", "amazon", "meta", "nvidia"}
        benchmark_company = company if normalized in leaders else "Microsoft"
        mode = "leader_optimization" if normalized in leaders else "benchmark_catchup"

        # -----------------------
        # CURRENT STATE
        # -----------------------
        state_query = (
            f"Target company: {company}\n"
            f"Benchmark company: {benchmark_company}\n"
            f"Mode: {mode}\n"
            "Provide concrete analysis points only."
        )
        current_state_response = rag.guardrails.apply_output(
            rag.ask(state_query, "analyze_state")
        )
        current_state_points = _extract_points(current_state_response, max_points=10)

        # -----------------------
        # PLAN
        # -----------------------
        plan_query = (
            f"Target company: {company}\n"
            f"Benchmark company: {benchmark_company}\n"
            f"Mode: {mode}\n"
            "Return prioritized improvements for 30/60/90 days."
        )
        todo_response = rag.guardrails.apply_output(
            rag.ask(plan_query, "analyze_plan")
        )
        todo_points = _extract_points(todo_response, max_points=10)

        final_current_state = current_state_points[:10]
        final_todo = [] if mode == "leader_optimization" else todo_points[:10]

        if not final_current_state:
            final_current_state = [
                "No strong evidence found in current context for a detailed state profile."
            ]

        if mode == "leader_optimization" and not final_todo:
            final_todo = ["No major improvements required for industry leaders."]

        if mode != "leader_optimization" and not final_todo:
            final_todo = [
                "No concrete initiatives were extracted from current context. Add more company-specific material."
            ]

        # -----------------------
        # METRICS
        # -----------------------
        metrics_query = (
            f"Target company: {company}\n"
            f"Benchmark company: {benchmark_company}\n"
            f"Mode: {mode}\n"
            "Generate maturity and revenue trajectory metrics."
        )
        metrics_raw = rag.guardrails.apply_output(
            rag.ask(metrics_query, "analyze_metrics")
        )
        maturity_score, focus_topics, revenue_series = _parse_metrics(metrics_raw)

        # -----------------------
        # SAVE TO DB
        # -----------------------
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO company_analyses (
                    username,
                    company_name,
                    current_state_json,
                    todo_plan_json,
                    benchmark_company,
                    maturity_score,
                    focus_topics_json,
                    revenue_series_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    company,
                    json.dumps(final_current_state, ensure_ascii=False),
                    json.dumps(final_todo, ensure_ascii=False),
                    benchmark_company,
                    maturity_score,
                    json.dumps(focus_topics, ensure_ascii=False),
                    json.dumps([point.model_dump() for point in revenue_series], ensure_ascii=False),
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
            benchmarkCompany=benchmark_company,
            maturityScore=maturity_score,
            focusTopics=focus_topics,
            revenueSeries=revenue_series,
            userRating=None,
            createdAt=row["created_at"],
        )

    except Exception as e:
        return CompanyAnalysisResponse(
            companyName=request.companyName,
            currentState=[
                f"Analysis in progress: {str(e)[:100]}",
                "RAG system is processing available documents",
                "Check if company documents are uploaded",
                "Try again with more specific company information",
            ],
            todoPlan=[
                "Ensure company documents are loaded into RAG system",
                "Verify document quality and relevance",
                "Run specific queries for better results",
                "Consider uploading additional company data",
            ],
            benchmarkCompany="Microsoft",
            maturityScore=None,
            focusTopics=[],
            revenueSeries=[],
            userRating=None,
        )
