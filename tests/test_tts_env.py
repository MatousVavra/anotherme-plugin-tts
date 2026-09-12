import pytest

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
