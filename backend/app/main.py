import json
from fastapi import FastAPI
from pydantic import BaseModel

from .gemini_service import generate_response
from .sheets_service import get_project_context

app = FastAPI(
    title="ISIRA Master Engine API",
    version="1.0.0",
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    project: str | None = None


class ChatResponse(BaseModel):
    response: str


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ISIRA Master Engine API",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    history = [
        {
            "role": item.role,
            "content": item.content,
        }
        for item in request.history
    ]

    project_context = (
        get_project_context(request.project)
        if request.project
        else ""
    )

    response_message = request.message

    if project_context:
        response_message = (
            f"Project Context:\n{project_context}\n\n"
            f"User Request:\n{request.message}"
        )

    response = generate_response(
        response_message,
        history,
    )

    return ChatResponse(response=response)

from fastapi import File, Form, UploadFile
from .image_service import analyze_image
from .storage_service import save_image


@app.post("/image/analyze")
async def image_analyze(
    file: UploadFile = File(...),
    prompt: str = Form("Analyze this image and describe the important details clearly."),
):
    image_bytes = await file.read()

    max_size = 10 * 1024 * 1024
    if len(image_bytes) > max_size:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=413,
            detail="Image file is too large. Maximum allowed size is 10 MB.",
        )

    mime_type = file.content_type or "image/jpeg"

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if mime_type not in allowed_types:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=415,
            detail="Unsupported image type. Allowed types: JPEG, PNG, WEBP.",
        )

    storage_path = save_image(
        image_bytes=image_bytes,
        mime_type=mime_type,
        original_filename=file.filename,
    )

    response = analyze_image(
        image_bytes=image_bytes,
        mime_type=mime_type,
        prompt=prompt,
    )

    return {
        "response": response,
        "filename": file.filename,
        "content_type": mime_type,
        "storage_path": storage_path,
    }

class ImageChatMessage(BaseModel):
    role: str
    content: str


@app.post("/chat/image")
async def image_chat(
    file: UploadFile = File(...),
    message: str = Form("Analyze this image."),
    history: str = Form("[]"),
    project: str | None = Form(None),
):
    image_bytes = await file.read()

    max_size = 10 * 1024 * 1024
    if len(image_bytes) > max_size:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=413,
            detail="Image file is too large. Maximum allowed size is 10 MB.",
        )

    mime_type = file.content_type or "image/jpeg"

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if mime_type not in allowed_types:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=415,
            detail="Unsupported image type. Allowed types: JPEG, PNG, WEBP.",
        )

    project_context = (
        get_project_context(project)
        if project
        else ""
    )

    storage_path = save_image(
        image_bytes=image_bytes,
        mime_type=mime_type,
        original_filename=file.filename,
    )

    try:
        parsed_history = json.loads(history)
        if not isinstance(parsed_history, list):
            raise ValueError("History must be a JSON list.")
    except (json.JSONDecodeError, ValueError):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Invalid history format. Expected a JSON list.",
        )

    response = analyze_image(
        image_bytes=image_bytes,
        mime_type=mime_type,
        prompt=message,
        history=parsed_history,
        project_context=project_context,
    )

    return {
        "response": response,
        "filename": file.filename,
        "content_type": mime_type,
        "storage_path": storage_path,
        "project": project,
    }

from .speech_service import transcribe_audio


@app.post("/voice/transcribe")
async def voice_transcribe(
    file: UploadFile = File(...),
    language_code: str = Form("te-IN"),
):
    audio_bytes = await file.read()

    if not audio_bytes:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Audio file is empty.",
        )

    transcript = transcribe_audio(
        audio_bytes=audio_bytes,
        language_code=language_code,
    )

    return {
        "transcript": transcript,
        "filename": file.filename,
        "content_type": file.content_type,
    }

from .tts_service import synthesize_speech

class TTSRequest(BaseModel):
    text: str
    language_code: str = "te-IN"


@app.post("/voice/synthesize")
def voice_synthesize(request: TTSRequest):
    if not request.text.strip():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty.",
        )

    audio_content = synthesize_speech(
        text=request.text,
        language_code=request.language_code,
    )

    from fastapi.responses import Response

    return Response(
        content=audio_content,
        media_type="audio/mpeg",
    )
