"""Offline tests for the Gemini research module, using a fake client (no network)."""
from datetime import datetime, timezone

import pytest
from google.genai import errors, types

from modules import ai_research
from modules.ai_research import ResearchError, research_company


def _response(text):
    return types.GenerateContentResponse.model_validate({
        "candidates": [{
            "content": {"role": "model", "parts": [{"text": text}]},
            "grounding_metadata": {
                "web_search_queries": ["query"],
                "grounding_chunks": [
                    {"web": {"uri": "https://example.com/1", "title": "one.com.au"}},
                    {"web": {"uri": "https://example.com/2", "title": "two.com.au"}},
                    {"web": {"uri": "https://example.com/1", "title": "duplicate"}},
                ],
                "search_entry_point": {"rendered_content": "<div>suggestions</div>"},
            },
        }]
    })


class FakeModels:
    def __init__(self, mode):
        self.mode, self.calls = mode, []

    def generate_content(self, model, contents, config):
        self.calls.append((model, contents, config))
        search = config.tools[0].google_search
        if self.mode == "quota":
            raise errors.ClientError(429, {"error": {"code": 429, "message": "Resource exhausted"}})
        if self.mode == "reject_filter" and search.time_range_filter is not None:
            raise errors.ClientError(400, {"error": {"code": 400, "message": "unsupported"}})
        return _response("news text" if "Notable news" in contents else "profile text")


@pytest.fixture
def fake_client(monkeypatch):
    def make(mode="ok"):
        client = type("FakeClient", (), {})()
        client.models = FakeModels(mode)
        monkeypatch.setattr(ai_research, "get_client", lambda api_key: client)
        return client
    return make


NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


def test_research_returns_profile_news_sources_and_suggestions(fake_client):
    client = fake_client()
    result = research_company("key", "Commonwealth Bank", "CBA.AX", now=NOW, model="test-model")

    assert result.profile.text == "profile text"
    assert result.news.text == "news text"
    assert result.profile.sources == [("one.com.au", "https://example.com/1"),
                                      ("two.com.au", "https://example.com/2")]  # de-duplicated
    assert result.news.search_suggestions_html == "<div>suggestions</div>"
    assert len(client.models.calls) == 2
    assert all(call[0] == "test-model" for call in client.models.calls)


def test_news_request_is_limited_to_last_30_days(fake_client):
    client = fake_client()
    research_company("key", "CBA", "CBA.AX", now=NOW)

    filters = {("news" if "Notable news" in c[1] else "profile"): c[2].tools[0].google_search.time_range_filter
               for c in client.models.calls}
    assert filters["profile"] is None
    assert filters["news"].end_time == NOW
    assert (filters["news"].end_time - filters["news"].start_time).days == 30


def test_falls_back_when_date_filter_rejected(fake_client):
    client = fake_client("reject_filter")
    result = research_company("key", "CBA", "CBA.AX", now=NOW)
    assert result.news.text == "news text"
    assert len(client.models.calls) == 3  # profile + rejected news + retried news


def test_quota_error_becomes_friendly_message(fake_client):
    fake_client("quota")
    with pytest.raises(ResearchError, match="quota"):
        research_company("key", "CBA", "CBA.AX", now=NOW)


def test_missing_api_key():
    with pytest.raises(ResearchError, match="No Gemini API key"):
        research_company("", "CBA", "CBA.AX")
