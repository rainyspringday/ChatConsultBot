from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.auth import get_current_user
from src.api.deps import get_rag
from src.core.db import get_connection, init_db
from src.services.rag_service import RAGService

router = APIRouter(prefix="/chats", tags=["chats"])
init_db()


class ChatCreateRequest(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=120)


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    createdAt: str


class ChatMessage(BaseModel):
    id: int
    role: str
    content: str
    rating: int | None = None
    createdAt: str


class ChatMessageRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class ChatAnswerResponse(BaseModel):
    answer: str
    messageId: int
    chatTitle: str


class ChatFeedbackRequest(BaseModel):
    rating: int = Field(..., ge=-1, le=1)


def _get_recent_chat_history(chat_id: int, limit: int = 8) -> list[dict[str, str]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, limit),
        ).fetchall()
    ordered = list(reversed(rows))
    return [{"role": row["role"], "content": row["content"]} for row in ordered]


def _get_chat_for_user(chat_id: int, username: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, title, created_at FROM chat_sessions WHERE id = ? AND username = ?",
            (chat_id, username),
        ).fetchone()
    return row


@router.get("", response_model=list[ChatSessionResponse])
def list_chats(username: str = Depends(get_current_user)):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, created_at
            FROM chat_sessions
            WHERE username = ?
            ORDER BY id DESC
            """,
            (username,),
        ).fetchall()
    return [
        ChatSessionResponse(id=row["id"], title=row["title"], createdAt=row["created_at"])
        for row in rows
    ]


@router.post("", response_model=ChatSessionResponse)
def create_chat(payload: ChatCreateRequest, username: str = Depends(get_current_user)):
    title = payload.title.strip() or "New chat"
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO chat_sessions (username, title) VALUES (?, ?)",
            (username, title),
        )
        chat_id = cursor.lastrowid
        row = conn.execute(
            "SELECT id, title, created_at FROM chat_sessions WHERE id = ?",
            (chat_id,),
        ).fetchone()
        conn.commit()
    return ChatSessionResponse(id=row["id"], title=row["title"], createdAt=row["created_at"])


@router.get("/{chat_id}/messages", response_model=list[ChatMessage])
def list_chat_messages(chat_id: int, username: str = Depends(get_current_user)):
    if not _get_chat_for_user(chat_id, username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                m.id,
                m.role,
                m.content,
                m.created_at,
                f.rating
            FROM chat_messages m
            LEFT JOIN chat_message_feedback f
                ON f.message_id = m.id AND f.username = ?
            WHERE m.chat_id = ?
            ORDER BY m.id ASC
            """,
            (username, chat_id),
        ).fetchall()
    return [
        ChatMessage(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            rating=row["rating"],
            createdAt=row["created_at"],
        )
        for row in rows
    ]


@router.delete("/{chat_id}")
def delete_chat(chat_id: int, username: str = Depends(get_current_user)):
    chat = _get_chat_for_user(chat_id, username)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    with get_connection() as conn:
        conn.execute("DELETE FROM chat_messages WHERE chat_id = ?", (chat_id,))
        conn.execute(
            "DELETE FROM chat_sessions WHERE id = ? AND username = ?",
            (chat_id, username),
        )
        conn.commit()
    return {"status": "deleted", "chatId": chat_id}


@router.post("/{chat_id}/messages", response_model=ChatAnswerResponse)
def send_message(
    chat_id: int,
    payload: ChatMessageRequest,
    rag: RAGService = Depends(get_rag),
    username: str = Depends(get_current_user),
):
    chat = _get_chat_for_user(chat_id, username)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question is required")

    history = _get_recent_chat_history(chat_id, limit=8)
    answer = rag.ask(question, chat_history=history).strip()
    final_title = chat["title"]
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, "user", question),
        )
        cursor = conn.execute(
            "INSERT INTO chat_messages (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, "assistant", answer),
        )
        assistant_message_id = cursor.lastrowid

        existing_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM chat_messages WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()["cnt"]
        if existing_count <= 2:
            generated_title = rag.generate_chat_title(question)
            final_title = generated_title or question[:60]
            conn.execute(
                "UPDATE chat_sessions SET title = ? WHERE id = ?",
                (final_title, chat_id),
            )
        conn.commit()

    return ChatAnswerResponse(
        answer=answer,
        messageId=assistant_message_id,
        chatTitle=final_title,
    )


@router.post("/{chat_id}/messages/{message_id}/feedback")
def rate_message(
    chat_id: int,
    message_id: int,
    payload: ChatFeedbackRequest,
    username: str = Depends(get_current_user),
):
    if not _get_chat_for_user(chat_id, username):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    with get_connection() as conn:
        msg = conn.execute(
            "SELECT id, role FROM chat_messages WHERE id = ? AND chat_id = ?",
            (message_id, chat_id),
        ).fetchone()
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )
        if msg["role"] != "assistant":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only assistant messages can be rated",
            )

        conn.execute(
            """
            INSERT INTO chat_message_feedback (message_id, username, rating)
            VALUES (?, ?, ?)
            ON CONFLICT(message_id, username)
            DO UPDATE SET rating = excluded.rating
            """,
            (message_id, username, payload.rating),
        )
        conn.commit()

    return {
        "status": "saved",
        "chatId": chat_id,
        "messageId": message_id,
        "rating": payload.rating,
    }
