import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.prompts import ANALYZE_SYSTEM, LETTER_SYSTEM
from app.sarvam import SarvamError, chat, parse_json, speak, transcribe

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
app = FastAPI(title="Shikayat Saathi")


class AnalyzeRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=6000)
    language: str = "unknown"
    followup_used: bool = False


class LetterRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=8000)
    language: str = "unknown"
    fields: dict[str, Any] = Field(default_factory=dict)


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2500)
    language: str = Field(min_length=2, max_length=16)


def fail(exc: SarvamError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))


def clean_analysis(value: dict[str, Any], followup_used: bool) -> dict[str, Any]:
    keys = ["language", "category", "department", "location", "since_when", "what_happened",
            "prior_attempts", "desired_resolution"]
    output = {key: value.get(key) if isinstance(value.get(key), str) else None for key in keys}
    output["missing"] = [item for item in value.get("missing", []) if item in keys] if isinstance(value.get("missing"), list) else []
    question = value.get("followup_question_native")
    output["followup_question_native"] = None if followup_used else question if isinstance(question, str) and question.strip() else None
    return output


@app.post("/api/transcribe")
async def api_transcribe(file: UploadFile = File(...)) -> dict[str, str]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Please record a short audio clip first.")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="That recording is too large. Please keep it under 25 MB.")
    try:
        return await transcribe(file.filename or "recording.webm", content, file.content_type or "audio/webm")
    except SarvamError as exc:
        raise fail(exc)


@app.post("/api/analyze")
async def api_analyze(request: AnalyzeRequest) -> dict[str, Any]:
    extra = "Do not ask a follow-up question; one has already been used." if request.followup_used else ""
    messages = [{"role": "system", "content": ANALYZE_SYSTEM}, {"role": "user", "content": f"Language hint: {request.language}. {extra}\n\nTranscript:\n{request.transcript}"}]
    try:
        return clean_analysis(parse_json(await chat(messages, 700)), request.followup_used)
    except SarvamError as exc:
        raise fail(exc)


@app.post("/api/letter")
async def api_letter(request: LetterRequest) -> dict[str, str]:
    context = json.dumps({"language": request.language, "transcript": request.transcript, "fields": request.fields}, ensure_ascii=False)
    try:
        result = parse_json(await chat([{"role": "system", "content": LETTER_SYSTEM}, {"role": "user", "content": context}], 900))
    except SarvamError as exc:
        raise fail(exc)
    if not all(isinstance(result.get(key), str) and result[key].strip() for key in ("letter_en", "letter_native")):
        raise HTTPException(status_code=502, detail="The AI did not return both letters. Please try again.")
    return {"letter_en": result["letter_en"].strip(), "letter_native": result["letter_native"].strip()}


@app.post("/api/speak")
async def api_speak(request: SpeakRequest) -> Response:
    if request.language == "unknown":
        raise HTTPException(status_code=400, detail="The language could not be identified, so audio is unavailable.")
    try:
        audio = await speak(request.text, request.language)
    except SarvamError as exc:
        raise fail(exc)
    return Response(content=audio, media_type="audio/wav")


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
