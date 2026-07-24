from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.chat_orchestrator import ChatOrchestrator
from app.schemas.schemas import ChatRequest, ChatResponse
from app.models.schema import Conversation, Message, User
import uuid

router = APIRouter(prefix="/api/chat", tags=["chat"])

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
    ai_response_text = orchestrator.process_input(text=request.message, user_id=current_user.id)

    # 5. Log AI message
    ai_msg = Message(
        conversation_id=request.sessionId,
        role="assistant",
        content=ai_response_text
    )
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
