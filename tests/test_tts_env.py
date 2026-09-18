import pytest
from openai import OpenAI

from conftest import load_plugin_module
from fake_plugin_context import FakePluginContext

_ENV_KEYS = ("TTS_BASE_URL", "TTS_API_KEY", "TTS_MODEL", "AI_BASE_URL", "AI_API_KEY")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """FakePluginContext falls back to os.environ; keep ambient values out
    so "nothing set" really means nothing set, in container and CI alike."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _api(env: dict):
    mod = load_plugin_module()
    return mod.TTSApi(FakePluginContext(env=env))


def test_settings_fall_back_to_ai_vars():
    api = _api({"AI_BASE_URL": "https://ai.example/v1/", "AI_API_KEY": "sk-ai", "TTS_MODEL": "my-tts"})
    assert api._settings() == ("https://ai.example/v1/", "sk-ai", "my-tts")


def test_settings_tts_vars_override_ai_vars():
    api = _api({
        "AI_BASE_URL": "https://ai.example/v1/", "AI_API_KEY": "sk-ai",
        "TTS_BASE_URL": "https://tts.example/v1/", "TTS_API_KEY": "sk-tts",
    })
    assert api._settings() == ("https://tts.example/v1/", "sk-tts", "tts-1")


def test_settings_defaults_when_nothing_set():
    api = _api({})
    assert api._settings() == ("https://llm.ai.e-infra.cz/v1/", "", "tts-1")


class _FakeSpeech:
    def __init__(self, client):
        self._client = client

    def create(self, **kwargs):
        self._client.last_kwargs = kwargs
        return type("Response", (), {"content": b"mp3-bytes"})()


class _FakeAudio:
    def __init__(self, client):
        self.speech = _FakeSpeech(client)


class _FakeClient:
    def __init__(self):
        self.last_kwargs = None
        self.audio = _FakeAudio(self)


class _HostLLM:
    def __init__(self, client):
        self._client = client
        self.calls = 0

    def get_client(self):
        self.calls += 1
        return self._client


def test_client_prefers_host_llm_client():
    fake = _FakeClient()
    host = _HostLLM(fake)
    mod = load_plugin_module()
    api = mod.TTSApi(FakePluginContext(env={}, llm_client=host))
    assert api._client() is fake
    assert host.calls == 1


def test_client_falls_back_to_env_built_client():
    mod = load_plugin_module()
    api = mod.TTSApi(FakePluginContext(env={"AI_BASE_URL": "https://ai.example/v1/", "AI_API_KEY": "sk-ai"}))
    assert isinstance(api._client(), OpenAI)


def test_synthesize_uses_host_client():
    fake = _FakeClient()
    host = _HostLLM(fake)
    mod = load_plugin_module()
    api = mod.TTSApi(FakePluginContext(env={}, llm_client=host))
    audio = api.synthesize("hello", "nova")
    assert audio == b"mp3-bytes"
    assert fake.last_kwargs["model"] == "tts-1"
    assert fake.last_kwargs["voice"] == "nova"
    assert fake.last_kwargs["input"] == "hello"


def _configured_api(config):
    fake = _FakeClient()
    host = _HostLLM(fake)
    mod = load_plugin_module()
    ctx = FakePluginContext(env={}, llm_client=host, config=config)
    return mod.TTSApi(ctx), fake


def test_synthesize_prefers_configured_voice_and_model():
    api, fake = _configured_api({"voice": "shimmer", "model": "my-tts"})
    api.synthesize("hello")
    assert fake.last_kwargs["voice"] == "shimmer"
    assert fake.last_kwargs["model"] == "my-tts"


def test_explicit_voice_beats_configured_voice():
    api, fake = _configured_api({"voice": "shimmer", "model": "my-tts"})
    api.synthesize("hello", "echo")
    assert fake.last_kwargs["voice"] == "echo"
    assert fake.last_kwargs["model"] == "my-tts"


def test_env_model_used_when_no_configured_model():
    fake = _FakeClient()
    host = _HostLLM(fake)
    mod = load_plugin_module()
    api = mod.TTSApi(FakePluginContext(env={"TTS_MODEL": "env-tts"}, llm_client=host))
    api.synthesize("hello")
    assert fake.last_kwargs["model"] == "env-tts"
    assert fake.last_kwargs["voice"] == "alloy"


def test_stored_settings_beat_env_model():
    fake = _FakeClient()
    host = _HostLLM(fake)
    mod = load_plugin_module()
    ctx = FakePluginContext(env={"TTS_MODEL": "env-tts"}, llm_client=host, config={"model": "stored-tts"})
    ctx.store.set("settings", {"voice": "fable"})
    api = mod.TTSApi(ctx)
    api.synthesize("hello")
    assert fake.last_kwargs["model"] == "stored-tts"
    assert fake.last_kwargs["voice"] == "fable"
