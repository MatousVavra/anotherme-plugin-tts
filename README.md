# anotherme-plugin-tts

Text-to-speech for [AnotherMe](https://github.com/MatousVavra/AnotherMe) via
an OpenAI-compatible `/v1/audio/speech` provider.

Extracted from the AnotherMe host repository at commit 9a6ef26 — prior
history lives there.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `TTS_BASE_URL` | falls back to `AI_BASE_URL` | Provider base URL |
| `TTS_API_KEY` | falls back to `AI_API_KEY` | Provider API key |
| `TTS_MODEL` | `tts-1` | TTS model name |

Settings (`model`, `voice`) are configurable per-install via the plugin
settings UI.

## Development

Unit tests run standalone against `FakePluginContext`:

    pip install fastapi pydantic httpx pyyaml pytest pytest-asyncio openai
    pytest tests/ --ignore=tests/integration

Integration tests run inside the released app image (see
`.github/workflows/test.yml`). To develop against a live app, point
`COMMUNITY_PLUGINS_DIR` at this checkout's parent directory.

## Releases

Tag `vX.Y.Z` (must match `plugin/plugin.yaml` `version`), then bump the tag
in the [community index](https://github.com/MatousVavra/anotherme-plugins).
