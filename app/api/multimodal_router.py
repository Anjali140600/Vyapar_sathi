"""
Multimodal Router — text, voice, image input endpoints.
Mirrors step2-multimodal's API surface, integrated into FastAPI with auth.

Endpoints:
  POST /api/upload            — save file + log to DB (existing, unchanged)
  POST /api/ocr               — OCR on previously uploaded file (existing)
  POST /api/stt               — STT on previously uploaded file (existing)

  POST /api/input/text        — pass-through text → {mode, recognizedText}
  POST /api/input/voice       — raw audio blob → Whisper → {mode, recognizedText}
  POST /api/input/image       — raw image → Tesseract → {mode, recognizedText}
  GET  /api/multimodal/health — service health / config report
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Body
from sqlalchemy.orm import Session
import os
import uuid
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.schema import UserDocument, User, Conversation
from app.services.ocr_service import OCRService
from app.services.stt_service import STTService

router = APIRouter(prefix="/api", tags=["multimodal"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── helpers ───────────────────────────────────────────────────────────────────

def _mime_to_ext(mime: str) -> str:
    mime = (mime or "").lower()
    if "wav" in mime:
        return ".wav"
    if "mpeg" in mime or "mp3" in mime:
        return ".mp3"
    if "mp4" in mime or "m4a" in mime:
        return ".m4a"
    if "ogg" in mime:
        return ".ogg"
    return ".webm"

# ── existing endpoints (unchanged) ────────────────────────────────────────────

@router.post("/upload")
async def upload_file(
    sessionId: Optional[str] = "",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_uuid = str(uuid.uuid4())
    ext = file.filename.split(".")[-1]
    filename = f"{file_uuid}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    valid_conv_id = None
    if sessionId:
        conv = db.query(Conversation).filter(
            Conversation.id == sessionId,
            Conversation.user_id == current_user.id,
        ).first()
        if conv:
            valid_conv_id = sessionId

    doc = UserDocument(
        user_id=current_user.id,
        conversation_id=valid_conv_id,
        file_name=filename,
        original_name=file.filename,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        mime_type=file.content_type,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"id": str(doc.id), "success": True, "file_uuid": file_uuid}


@router.post("/ocr")
def run_ocr(
    fileId: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(UserDocument).filter(
        UserDocument.id == fileId,
        UserDocument.user_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    ocr_service = OCRService()
    result = ocr_service.process_image(doc.file_path)
    return {"success": True, "text": result.get("raw_text"), "extracted_data": result}


@router.post("/stt")
def run_stt(
    fileId: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(UserDocument).filter(
        UserDocument.id == fileId,
        UserDocument.user_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    stt = STTService()
    try:
        transcript = stt.transcribe(doc.file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "transcript": transcript}

# ── step-2 style direct input endpoints ──────────────────────────────────────

@router.post("/input/text")
def input_text(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    """Pass-through text input. Body: {\"text\": \"...\"}"""
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    return {"mode": "text", "recognizedText": text}


@router.post("/input/voice")
async def input_voice(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Accept raw audio blob (webm/mp4/wav/mp3) from browser MediaRecorder or file upload.
    Converts via ffmpeg → transcribes with Whisper CLI.
    Returns {mode, recognizedText, whisperModel, whisperLanguage}.
    """
    if not audio:
        raise HTTPException(status_code=400, detail="Audio file is required")

    audio_bytes = await audio.read()
    ext = _mime_to_ext(audio.content_type)

    stt = STTService()
    try:
        transcript = stt.transcribe_bytes(audio_bytes, suffix=ext)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    return {
        "mode": "voice",
        "recognizedText": transcript or "No speech recognized",
        "whisperModel": os.getenv("WHISPER_MODEL", "base"),
        "whisperLanguage": os.getenv("WHISPER_LANGUAGE", "en"),
    }


@router.post("/input/image")
async def input_image(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Accept raw image bytes. Runs Tesseract OCR.
    Returns {mode, recognizedText, tesseractLangs}.
    """
    if not image:
        raise HTTPException(status_code=400, detail="Image file is required")

    import tempfile, shutil
    image_bytes = await image.read()
    ext = "." + (image.filename.split(".")[-1] if image.filename else "png")
    tmp_dir = tempfile.mkdtemp(prefix="vyapar-ocr-")
    try:
        img_path = os.path.join(tmp_dir, f"input{ext}")
        with open(img_path, "wb") as f:
            f.write(image_bytes)
        ocr = OCRService()
        result = ocr.process_image(img_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    langs = os.getenv("TESSERACT_LANGS", "eng+hin")
    return {
        "mode": "image",
        "recognizedText": (result.get("raw_text") or "").strip() or "No text found in image",
        "tesseractLangs": langs,
        "extractedData": result,
    }


@router.get("/multimodal/health")
def multimodal_health(current_user: User = Depends(get_current_user)):
    """Report multimodal service configuration (mirrors step2 /api/health)."""
    from app.services.stt_service import _ffmpeg_path
    ffmpeg_exec = _ffmpeg_path()
    langs = os.getenv("TESSERACT_LANGS", "eng+hin")
    return {
        "ok": True,
        "service": "vyapar-sathi-multimodal",
        "engine": {
            "voice": "OpenAI Whisper (local CLI)",
            "image": "Tesseract (pytesseract)",
        },
        "whisperModel": os.getenv("WHISPER_MODEL", "base"),
        "whisperLanguage": os.getenv("WHISPER_LANGUAGE", "en"),
        "whisperFP16": os.getenv("WHISPER_FP16", "false"),
        "tesseractLangs": langs,
        "ffmpegPath": ffmpeg_exec or "not found — install ffmpeg",
        "condaPrefix": os.getenv("CONDA_PREFIX", "not set"),
    }
