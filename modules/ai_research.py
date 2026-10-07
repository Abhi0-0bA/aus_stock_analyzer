"""
AI company research using Google Gemini with "Grounding with Google Search".

Gemini decides what to search for, reads the results and writes a summary, so
the model itself is the "reasoning search engine". Each result includes the
web sources Gemini used and Google's Search Suggestions HTML.

Terms to respect (Gemini API Additional Terms, "Grounding with Google Search"):
- Grounded results must be shown together with their Search Suggestions.
- Grounded results must not be modified, mixed with other content, or cached
  and reused for other users. The app therefore keeps results only in the
  current user's session (st.session_state), never in a shared cache.
- Search grounding is not available on the free tier for current models; the
  Google AI Studio project needs billing enabled.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

DEFAULT_MODEL = "gemini-3.8-flash"
NEWS_WINDOW_DAYS = 30


class ResearchError(Exception):
    """A user-presentable error from the AI research step."""


@dataclass
class GroundedResult:
    text: str
    sources: list = field(default_factory=list)       # [(title, url), ...]
    search_suggestions_html: str = ""                  # Google's rendered Search Suggestions
    search_queries: list = field(default_factory=list)


@dataclass
class CompanyResearch:
    profile: GroundedResult
    news: GroundedResult
    news_start: datetime
    news_end: datetime
    model: str
    generated_at: datetime


PROFILE_PROMPT = """You are a careful equity research assistant. Use Google Search to research \
{company} (ticker {ticker} on the Australian Securities Exchange; sector: {sector}; industry: {industry}).

Write a factual company briefing in Markdown with these sections, each as a level-3 heading (###):
### Overview
### Business model and revenue drivers
### Competitive position
### Leadership and governance
### Strategy and recent developments
### Key risks

Rules:
- Base every statement on what you find in search results; if you cannot find something, say so briefly.
- Prefer primary sources (company announcements, annual reports, ASX releases) and reputable financial media.
- Include specific figures and dates where available, and say which period they refer to.
- Do not give investment advice, buy/sell recommendations or price predictions.
- Keep it to roughly 400-600 words."""

NEWS_PROMPT = """You are a careful financial news analyst. Use Google Search to find news about \
{company} (ticker {ticker} on the Australian Securities Exchange) published between {start} and {end}.

Respond in Markdown with exactly these two parts:

### Summary
One paragraph (4-6 sentences) explaining the main themes of the period and why they matter for the company.

### Notable news
A bullet list of the most significant distinct news items, newest first, up to 12 items. Format each as:
- **YYYY-MM-DD** - one or two sentences in your own words: what happened and why it matters.

Rules:
- Only include items published within {start} to {end}; skip anything outside that range.
- Merge duplicate coverage of the same event into one item.
- If you find little or no news in the period, say so plainly rather than padding.
- Do not give investment advice, buy/sell recommendations or price predictions."""


def get_client(api_key):
    """Creates a Gemini client. Imported lazily so the rest of the app works without the package."""
    try:
        from google import genai
    except ImportError as exc:
        raise ResearchError("The google-genai package is not installed. Run: pip install -r requirements.txt") from exc
    return genai.Client(api_key=api_key)


def _friendly_error(exc):
    """Turns a Gemini API error into a message the user can act on."""
    code = getattr(exc, "code", None)
    message = str(getattr(exc, "message", "") or exc)
    if code in (401, 403) or "API key" in message:
        return "Gemini rejected the API key. Check GEMINI_API_KEY in .streamlit/secrets.toml."
    if code == 429:
        return "Gemini quota or rate limit reached. Wait a minute and try again, or check your plan's limits."
    if code == 404:
        return f"Gemini model not found. Set GEMINI_MODEL in .streamlit/secrets.toml to a current model. ({message})"
    if code == 400 and ("billing" in message.lower() or "free tier" in message.lower()):
        return "Google Search grounding needs billing enabled on your Google AI Studio project."
    if code and 500 <= int(code) < 600:
        return "Gemini is temporarily unavailable. Try again shortly."
    return f"AI research failed: {message}"


def _parse_response(response):
    """Extracts text, sources, search suggestions and queries from a grounded response."""
    text = (getattr(response, "text", None) or "").strip()
    sources, seen = [], set()
    suggestions_html, queries = "", []

    candidates = getattr(response, "candidates", None) or []
    metadata = getattr(candidates[0], "grounding_metadata", None) if candidates else None
    if metadata:
        for chunk in getattr(metadata, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            uri = getattr(web, "uri", None) if web else None
            if uri and uri not in seen:
                seen.add(uri)
                sources.append((getattr(web, "title", None) or getattr(web, "domain", None) or uri, uri))
        entry_point = getattr(metadata, "search_entry_point", None)
        suggestions_html = (getattr(entry_point, "rendered_content", None) or "") if entry_point else ""
        queries = list(getattr(metadata, "web_search_queries", None) or [])

    if not text:
        raise ResearchError("Gemini returned an empty answer. Try again.")
    return GroundedResult(text=text, sources=sources,
                          search_suggestions_html=suggestions_html, search_queries=queries)


def _grounded_generate(client, model, prompt, time_range=None):
    """Runs one Gemini request with Google Search grounding."""
    from google.genai import errors, types

    def call(search):
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=search)],
            # Only Google's built-in search tool is used; no local Python functions to call.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        return client.models.generate_content(model=model, contents=prompt, config=config)

    try:
        if time_range:
            start, end = time_range
            try:
                response = call(types.GoogleSearch(
                    time_range_filter=types.Interval(start_time=start, end_time=end)))
            except errors.ClientError as exc:
                if exc.code != 400:
                    raise
                # If this model rejects the date filter, fall back to an unfiltered
                # search; the prompt still restricts the answer to the date range.
                response = call(types.GoogleSearch())
        else:
            response = call(types.GoogleSearch())
    except errors.APIError as exc:
        raise ResearchError(_friendly_error(exc)) from exc
    except Exception as exc:  # network problems etc.
        raise ResearchError(f"AI research failed: {exc}") from exc

    return _parse_response(response)


def research_company(api_key, company, ticker, sector="", industry="", model=DEFAULT_MODEL, now=None):
    """
    Runs the company briefing and the last-30-days news summary in parallel and
    returns a CompanyResearch. Raises ResearchError with a user-friendly message.
    """
    if not api_key:
        raise ResearchError("No Gemini API key configured.")
    client = get_client(api_key)

    news_end = now or datetime.now(timezone.utc)
    news_start = news_end - timedelta(days=NEWS_WINDOW_DAYS)
    details = dict(company=company, ticker=ticker,
                   sector=sector or "unknown", industry=industry or "unknown")
    profile_prompt = PROFILE_PROMPT.format(**details)
    news_prompt = NEWS_PROMPT.format(**details, start=news_start.date().isoformat(),
                                     end=news_end.date().isoformat())

    with ThreadPoolExecutor(max_workers=2) as pool:
        profile_job = pool.submit(_grounded_generate, client, model, profile_prompt)
        news_job = pool.submit(_grounded_generate, client, model, news_prompt, (news_start, news_end))
        profile, news = profile_job.result(), news_job.result()

    return CompanyResearch(profile=profile, news=news, news_start=news_start, news_end=news_end,
                           model=model, generated_at=datetime.now(timezone.utc))
