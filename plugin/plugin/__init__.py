import asyncio

from openai import OpenAI

from fastapi import APIRouter, HTTPException, Response

from pydantic import BaseModel


class TTSRequest(BaseModel):
    text: str
    voice: str = "alloy"


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

    def synthesize(self, text: str, voice: str = "alloy", model: str | None = None) -> bytes:
        base_url, api_key, default_model = self._settings()
        client = OpenAI(base_url=base_url, api_key=api_key)
        response = client.audio.speech.create(
            model=model or default_model,
            voice=voice,
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
            except Exception as e:
                msg = str(e)
                if "tts" in msg.lower() or "audio/speech" in msg.lower():
                    raise HTTPException(503, "TTS not supported by current AI provider. Set TTS_BASE_URL and TTS_API_KEY in .env for a provider that supports /v1/audio/speech (e.g. OpenAI).")
                raise HTTPException(500, f"TTS failed: {e}")

        ctx.register_router(router)
        ctx.register_api("tts", tts_api)
