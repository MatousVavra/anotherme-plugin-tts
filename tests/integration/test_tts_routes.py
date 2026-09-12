"""Route tests for the tts plugin (moved from the AnotherMe host repo,
tests/test_plugins/test_leaf_plugins.py)."""
from unittest.mock import patch

import pytest


@pytest.fixture
def client(make_client):
    return make_client()


def _get_tts_api():
    import src.main
    return src.main.plugin_manager.get_registry().get_api("tts")


def test_tts_route_returns_audio(client):
    with patch.object(_get_tts_api(), "synthesize", return_value=b"\xff\xfbaudiobytes"):
        resp = client.post("/plugins/tts", json={"text": "Hello", "voice": "alloy"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == b"\xff\xfbaudiobytes"


def test_tts_route_503_when_provider_lacks_speech(client):
    with patch.object(_get_tts_api(), "synthesize", side_effect=Exception("POST /v1/audio/speech Not Found")):
        assert client.post("/plugins/tts", json={"text": "x", "voice": "alloy"}).status_code == 503


def test_tts_route_500_on_other_errors(client):
    with patch.object(_get_tts_api(), "synthesize", side_effect=Exception("boom")):
        assert client.post("/plugins/tts", json={"text": "x", "voice": "alloy"}).status_code == 500


def test_tts_api_registered(client):
    api = _get_tts_api()
    assert api is not None
    with patch.object(api, "synthesize", return_value=b"mp3"):
        assert api.synthesize("hi") == b"mp3"
