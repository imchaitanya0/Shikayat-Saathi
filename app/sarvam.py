import base64
import json
import os
from typing import Any

import httpx

API_BASE = "https://api.sarvam.ai"


class SarvamError(Exception):
    """A safe, user-facing error from the upstream service."""


def _key() -> str:
    key = os.getenv("SARVAM_API_KEY")
    if not key:
        raise SarvamError("Server setup is incomplete. Add SARVAM_API_KEY to .env and restart.")
    return key


async def _request(path: str, *, json_body: dict[str, Any] | None = None,
                   files: dict[str, tuple[str, bytes, str]] | None = None,
                   data: dict[str, str] | None = None) -> dict[str, Any]:
    headers = {"api-subscription-key": _key()}
    timeout = httpx.Timeout(45.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{API_BASE}{path}", headers=headers, json=json_body, files=files, data=data
            )
    except httpx.HTTPError as exc:
        raise SarvamError("Could not reach Sarvam. Check your internet connection and try again.") from exc
    if response.status_code >= 400:
        raise SarvamError("Sarvam could not process this request. Please try again with a short, clear recording.")
    try:
        return response.json()
    except ValueError as exc:
        raise SarvamError("Sarvam returned an unexpected response. Please try again.") from exc


async def transcribe(filename: str, content: bytes, content_type: str) -> dict[str, Any]:
    payload = await _request(
        "/speech-to-text",
        files={"file": (filename or "recording.webm", content, content_type or "audio/webm")},
        data={"model": "saaras:v4", "language_code": "unknown"},
    )
    return {"transcript": payload.get("transcript", ""), "language": payload.get("language_code") or "unknown"}


async def chat(messages: list[dict[str, str]], max_tokens: int) -> str:
    payload = await _request(
        "/v1/chat/completions",
        json_body={
            "model": "sarvam-105b", "messages": messages, "temperature": 0.1,
            "reasoning_effort": "low", "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        },
    )
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SarvamError("Sarvam did not return a usable answer. Please try again.") from exc


def parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SarvamError("The AI response was incomplete. Please try again.") from exc
    if not isinstance(value, dict):
        raise SarvamError("The AI response had the wrong format. Please try again.")
    return value


async def speak(text: str, language: str) -> bytes:
    payload = await _request(
        "/text-to-speech",
        json_body={
            "text": text, "language_code": language, "model": "bulbul:v3",
            "speaker": "shubh", "output_audio_codec": "wav", "pace": 1.0,
        },
    )
    try:
        return base64.b64decode(payload["audios"][0], validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise SarvamError("Sarvam did not return playable audio. Please try again.") from exc
