def parse_news_item(item):
    """
    Normalises one yfinance news item into (title, link, publisher).

    Newer yfinance versions nest article fields under a "content" object
    (e.g. content.canonicalUrl.url); older versions returned flat keys
    ("title", "link", "publisher"). Both shapes are supported.
    """
    if not isinstance(item, dict):
        return "Untitled", None, "Unknown"

    content = item.get("content") or item
    title = content.get("title") or "Untitled"
    link = (
        (content.get("canonicalUrl") or {}).get("url")
        or (content.get("clickThroughUrl") or {}).get("url")
        or content.get("link")
    )
    publisher = (
        (content.get("provider") or {}).get("displayName")
        or content.get("publisher")
        or "Unknown"
    )
    return title, link, publisher


def get_dividend_yield_pct(info, price=None):
    """
    Returns the dividend yield as a percentage (e.g. 4.1 means 4.1%), or None.

    Computed as annual dividend per share / share price. Yahoo's own
    "dividendYield" field has changed units over time (fraction vs percent),
    so it is deliberately not used.
    """
    if not info:
        return None
    annual_dividend = info.get("dividendRate") or info.get("trailingAnnualDividendRate")
    price = price or info.get("currentPrice") or info.get("regularMarketPrice")
    try:
        annual_dividend = float(annual_dividend)
        price = float(price)
    except (TypeError, ValueError):
        return None
    if annual_dividend <= 0 or price <= 0:
        return None
    return annual_dividend / price * 100


def _to_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None  # filter out NaN


def _money(value):
    number = _to_float(value)
    return f"${number:,.2f}" if number is not None else None


def _compact(value):
    number = _to_float(value)
    if number is None:
        return None
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(number) >= limit:
            return f"{number / limit:.2f}{suffix}"
    return f"{number:,.0f}"


def _range(low, high):
    low, high = _money(low), _money(high)
    return f"{low} – {high}" if low and high else None


def build_key_stats(info):
    """
    Returns a list of (label, value) pairs for the key statistics panel,
    skipping anything Yahoo didn't provide. Only fields with unambiguous
    units are used (prices, counts and plain ratios).
    """
    if not info:
        return []

    pe_forward = _to_float(info.get("forwardPE"))
    beta = _to_float(info.get("beta"))
    price_to_book = _to_float(info.get("priceToBook"))
    employees = _to_float(info.get("fullTimeEmployees"))

    consensus = None
    recommendation = info.get("recommendationKey")
    if recommendation and recommendation != "none":
        consensus = str(recommendation).replace("_", " ").title()
        analysts = _to_float(info.get("numberOfAnalystOpinions"))
        if analysts:
            consensus += f" ({analysts:.0f} analysts)"

    stats = [
        ("Previous close", _money(info.get("previousClose"))),
        ("Day range", _range(info.get("dayLow"), info.get("dayHigh"))),
        ("52-week range", _range(info.get("fiftyTwoWeekLow"), info.get("fiftyTwoWeekHigh"))),
        ("Volume", _compact(info.get("volume"))),
        ("Avg. volume", _compact(info.get("averageVolume"))),
        ("EPS (trailing)", _money(info.get("trailingEps"))),
        ("Forward P/E", f"{pe_forward:.2f}" if pe_forward is not None else None),
        ("Price / book", f"{price_to_book:.2f}" if price_to_book is not None else None),
        ("Beta", f"{beta:.2f}" if beta is not None else None),
        ("Analyst target (mean)", _money(info.get("targetMeanPrice"))),
        ("Analyst consensus", consensus),
        ("Employees", f"{employees:,.0f}" if employees else None),
    ]
    return [(label, value) for label, value in stats if value]


def format_news(news_list):
    """
    Formats the raw news list into a readable string.
    """
    if not news_list:
        return "No recent news found."

    formatted_news = []
    for idx, item in enumerate(news_list[:5], 1):
        title, link, publisher = parse_news_item(item)
        formatted_news.append(f"{idx}. {title} (by {publisher})\n   Link: {link or 'No Link'}")
    
    return "\n\n".join(formatted_news)

def generate_report(data):
    """
    Generates a comprehensive report from the fetched stock data.
    """
    if not data:
        return "No data available to generate report."
    
    info = data.get('info', {})
    news = data.get('news', [])
    
    report = []
    report.append("="*40)
    report.append(f"STOCK ANALYSIS REPORT: {info.get('shortName', 'Unknown Stock')}")
    report.append("="*40)
    
    report.append(f"\n--- Overview ---")
    report.append(f"Sector: {info.get('sector', 'N/A')}")
    report.append(f"Industry: {info.get('industry', 'N/A')}")
    report.append(f"Business Summary: {info.get('longBusinessSummary', 'No summary available.')}")
    
    report.append(f"\n--- Financial Highlights ---")
    report.append(f"Current Price: {info.get('currentPrice', 'N/A')} {info.get('currency', 'N/A')}")
    report.append(f"Market Cap: {info.get('marketCap', 'N/A')}")
    report.append(f"PE Ratio: {info.get('trailingPE', 'N/A')}")
    dividend_yield = get_dividend_yield_pct(info)
    report.append(f"Dividend Yield: {f'{dividend_yield:.2f}%' if dividend_yield is not None else 'N/A'}")
    
    report.append(f"\n--- Latest News ---")
    report.append(format_news(news))
    
    return "\n".join(report)
