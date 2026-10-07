import math

from modules.analyzer import build_key_stats, format_news, get_dividend_yield_pct, parse_news_item


def test_parse_news_item_new_nested_format():
    item = {
        "id": "1",
        "content": {
            "title": "CBA flags steady margins",
            "canonicalUrl": {"url": "https://example.com/a"},
            "provider": {"displayName": "Reuters"},
        },
    }
    assert parse_news_item(item) == ("CBA flags steady margins", "https://example.com/a", "Reuters")


def test_parse_news_item_old_flat_format():
    item = {"title": "Old headline", "link": "https://example.com/b", "publisher": "AAP"}
    assert parse_news_item(item) == ("Old headline", "https://example.com/b", "AAP")


def test_parse_news_item_handles_missing_fields():
    assert parse_news_item({}) == ("Untitled", None, "Unknown")
    assert parse_news_item(None) == ("Untitled", None, "Unknown")


def test_format_news_empty():
    assert format_news([]) == "No recent news found."


def test_dividend_yield_from_rate_and_price():
    assert math.isclose(get_dividend_yield_pct({"dividendRate": 4.65}, 150.0), 3.1)


def test_dividend_yield_falls_back_to_trailing_rate_and_info_price():
    info = {"trailingAnnualDividendRate": 2.0, "currentPrice": 50.0}
    assert math.isclose(get_dividend_yield_pct(info), 4.0)


def test_dividend_yield_ignores_yahoo_dividend_yield_field():
    # Yahoo's dividendYield units have changed over time, so it must not be used.
    assert get_dividend_yield_pct({"dividendYield": 4.1, "currentPrice": 100}) is None


def test_dividend_yield_invalid_inputs():
    assert get_dividend_yield_pct({}) is None
    assert get_dividend_yield_pct({"dividendRate": 0, "currentPrice": 10}) is None
    assert get_dividend_yield_pct({"dividendRate": "n/a", "currentPrice": 10}) is None


def test_build_key_stats_formats_and_skips_missing():
    stats = dict(build_key_stats({
        "fiftyTwoWeekLow": 138.2, "fiftyTwoWeekHigh": 175.9,
        "volume": 2_100_000, "beta": float("nan"),
        "recommendationKey": "strong_buy", "numberOfAnalystOpinions": 14,
    }))
    assert stats["52-week range"] == "$138.20 – $175.90"
    assert stats["Volume"] == "2.10M"
    assert stats["Analyst consensus"] == "Strong Buy (14 analysts)"
    assert "Beta" not in stats  # NaN is skipped
    assert "Day range" not in stats  # missing is skipped


def test_build_key_stats_empty():
    assert build_key_stats({}) == []
    assert build_key_stats(None) == []
