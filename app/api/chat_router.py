import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.schema import Conversation, Message, User
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.chat_orchestrator import ChatOrchestrator

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _history_limit() -> int:
    try:
        value = int(os.getenv("AGENT_HISTORY_LIMIT", "8"))
    except ValueError:
        value = 8
    return max(2, min(value, 10))


def _safe_trace_metadata(trace: list[dict]) -> dict | None:
    if not trace:
        return None
    metadata = {
        "agent": {
            "steps": [
                {
                    "step": item.get("step"),
                    "tool": item.get("tool"),
                    "status": item.get("status"),
                    **({"duration_ms": item.get("duration_ms")} if item.get("duration_ms") is not None else {}),
                    **({"summary": item.get("summary")} if item.get("summary") else {}),
                }
                for item in trace
                if isinstance(item, dict)
            ]
        }
    }
    try:
        json.dumps(metadata)
    except (TypeError, ValueError):
        return None
    return metadata

@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Ensure/Create Session
    requested_session_id = (request.sessionId or "").strip()
    if not requested_session_id or requested_session_id == "web-session":
        request.sessionId = str(uuid.uuid4())
    else:
        request.sessionId = requested_session_id
    
    # 2. Get/Create Conversation in DB
    conversation = db.query(Conversation).filter(
        Conversation.id == request.sessionId,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        conversation = Conversation(id=request.sessionId, user_id=current_user.id, title="New Chat")
        db.add(conversation)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            request.sessionId = str(uuid.uuid4())
            conversation = Conversation(id=request.sessionId, user_id=current_user.id, title="New Chat")
            db.add(conversation)
            db.commit()

    prior_messages = db.query(Message).filter(
        Message.conversation_id == request.sessionId
    ).order_by(Message.created_at.asc(), Message.id.asc()).all()
    history = [
        {"role": message.role, "content": message.content}
        for message in prior_messages[-_history_limit():]
        if message.role in {"user", "assistant"} and message.content
    ]

    # 3. Log user message & Auto-Naming
    if request.message:
        # Auto-Rename if it's a new chat
        if conversation.title == "New Chat":
            conversation.title = (request.message[:40] + "...") if len(request.message) > 40 else request.message
            db.commit()

        user_msg = Message(
            conversation_id=request.sessionId,
            role="user",
            content=request.message
        )
        db.add(user_msg)
        db.commit()

    # 4. Orchestrate Response
    orchestrator = ChatOrchestrator(db)
    agent_response = orchestrator.process_input_with_trace(
        text=request.message,
        user_id=current_user.id,
        conversation_history=history,
    )
    ai_response_text = agent_response.answer

    # 5. Log AI message
    ai_msg = Message(
        conversation_id=request.sessionId,
        role="assistant",
        content=ai_response_text,
    )
    trace_metadata = _safe_trace_metadata(agent_response.trace)
    if trace_metadata:
        ai_msg.meta_data = trace_metadata
    db.add(ai_msg)
    db.commit()

    return {
        "success": True,
        "data": {
            "answer": ai_response_text,
            "sessionId": request.sessionId
        }
    }

@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convs = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.created_at.desc()).limit(20).all()
    return {
        "success": True,
        "data": [{"id": c.id, "title": c.title, "date": str(c.created_at)} for c in convs]
    }

@router.get("/history/{sessionId}")
def get_history(
    sessionId: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = db.query(Conversation).filter(
        Conversation.id == sessionId,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = db.query(Message).filter(
        Message.conversation_id == sessionId
    ).order_by(Message.created_at.asc()).all()
    return {
        "success": True,
        "data": [{"role": m.role, "content": m.content} for m in messages]
    }

@router.delete("/{sessionId}")
def delete_chat(
    sessionId: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = db.query(Conversation).filter(
        Conversation.id == sessionId,
        Conversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Chat not found")

    db.delete(conversation)
    db.commit()
    return {"success": True}
