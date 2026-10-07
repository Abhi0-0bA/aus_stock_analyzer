import pytest

from modules.fetcher import normalize_ticker


@pytest.mark.parametrize("raw, expected", [
    ("cba", "CBA.AX"),
    (" bhp.ax ", "BHP.AX"),
    ("^axjo", "^AXJO"),
    ("AAPL.US", "AAPL.US"),
])
def test_normalize_ticker_valid(raw, expected):
    assert normalize_ticker(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", None, "<script>", "CBA AX", "A" * 20])
def test_normalize_ticker_invalid(raw):
    assert normalize_ticker(raw) is None
