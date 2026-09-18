import asyncio
from typing import Literal

import openai
from openai import OpenAI

from fastapi import APIRouter, HTTPException, Response

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] | None = None


class TTSApi:
    def __init__(self, ctx):
        self._ctx = ctx

    def _settings(self) -> tuple[str, str, str]:
        """(base_url, api_key, model) with the same fallbacks src.config
        used: TTS_* falls back to AI_* falls back to hard defaults."""
        base_url = (
            self._ctx.get_env("TTS_BASE_URL")
            or self._ctx.get_env("AI_BASE_URL")
            or "https://llm.ai.e-infra.cz/v1/"
        )
        api_key = self._ctx.get_env("TTS_API_KEY") or self._ctx.get_env("AI_API_KEY") or ""
        model = self._ctx.get_env("TTS_MODEL") or "tts-1"
        return base_url, api_key, model

    def _configured(self, key: str) -> str | None:
        value = (self._ctx.get_config() or {}).get(key)
        return value if isinstance(value, str) and value else None

    def resolve_voice(self, requested: str | None = None) -> str:
        return requested or self._configured("voice") or "alloy"

    def resolve_model(self) -> str:
        return self._configured("model") or self._settings()[2]

    def _client(self) -> OpenAI:
        llm = getattr(self._ctx, "llm_client", None)
        if llm is not None and hasattr(llm, "get_client"):
            return llm.get_client()
        base_url, api_key, _ = self._settings()
        return OpenAI(base_url=base_url, api_key=api_key)

    def synthesize(self, text: str, voice: str | None = None, model: str | None = None) -> bytes:
        client = self._client()
        response = client.audio.speech.create(
            model=model or self.resolve_model(),
            voice=self.resolve_voice(voice),
            input=text,
            response_format="mp3",
        )
        return response.content


class Plugin:
    def on_load(self, ctx):
        tts_api = TTSApi(ctx)

        router = APIRouter()

        @router.post("")
        async def tts(body: TTSRequest):
            try:
                audio = await asyncio.to_thread(tts_api.synthesize, body.text, body.voice)
                return Response(content=audio, media_type="audio/mpeg")
            except openai.NotFoundError:
                raise HTTPException(503, "TTS not supported by current AI provider. Set TTS_BASE_URL and TTS_API_KEY in .env for a provider that supports /v1/audio/speech (e.g. OpenAI).")
            except Exception as e:
                raise HTTPException(500, f"TTS failed: {e}")

        ctx.register_router(router)
        ctx.register_api("tts", tts_api)
