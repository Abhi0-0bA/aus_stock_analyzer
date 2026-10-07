import html
import os

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from modules.fetcher import get_stock_data, get_live_price, scrape_company_website, normalize_ticker
from modules.analyzer import parse_news_item, get_dividend_yield_pct, build_key_stats
from modules.ai_research import DEFAULT_MODEL, NEWS_WINDOW_DAYS, ResearchError, research_company

st.set_page_config(
    page_title="Australian Stock Market Analyzer", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Chart accent: one gold that passes contrast checks on both the light and dark backgrounds.
CHART_GOLD = "#ad7d1a"

# Luxury Minimalist Styling
# Colours and fonts come from .streamlit/config.toml ([theme.light] / [theme.dark]),
# so this CSS must not set any colours - otherwise dark mode breaks.
st.markdown("""
    <style>
    /* Resolution scaling: Streamlit sizes text and spacing in rem, so scaling the
       root font size with the window width scales the whole UI. The browser
       already knows the viewer's window size (and OS display scaling), so no
       screen-resolution detection is needed.
       ~16px on laptops and phones, ~18px at 1920px wide, ~20px at 2560px (2K), max 22px. */
    html {
        font-size: clamp(16px, calc(0.35vw + 11px), 22px) !important;
    }

    /* Use the width of large screens instead of a narrow centred column. */
    .block-container, [data-testid="stMainBlockContainer"] {
        max-width: min(1760px, 100%) !important;
        padding: 2.5rem clamp(1rem, 4vw, 4rem) 5rem !important;
    }

    h1, h2, h3 {
        letter-spacing: -0.02em !important;
    }

    .stMarkdown p, .stMarkdown li {
        line-height: 1.65;
    }

    /* Home screen */
    .hero {
        text-align: center;
        padding: clamp(2rem, 12vh, 9rem) 0 2rem;
    }
    .hero h1 {
        font-size: clamp(2.4rem, 4.2vw, 4.75rem) !important;
        margin-bottom: 0.75rem;
    }
    .hero p {
        font-size: 1.25rem !important;
        font-weight: 300;
        opacity: 0.7;
    }

    /* Analysis header */
    .company-title {
        font-size: clamp(2rem, 3vw, 3.25rem) !important;
        margin-bottom: 0.25rem;
    }
    .company-subtitle {
        font-size: 1.15rem !important;
        opacity: 0.7;
    }

    /* Metrics - minimalist (translucent grey border works on light and dark) */
    [data-testid="stMetric"] {
        background: transparent !important;
        border-bottom: 1px solid rgba(128, 128, 128, 0.3) !important;
        box-shadow: none !important;
        padding: 0.6rem 0 !important;
    }
    [data-testid="stMetricLabel"] p {
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.8rem !important;
        opacity: 0.75;
    }

    /* Key statistics grid: as many columns as fit, so it adapts from phone to 2K */
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr));
        gap: 1.25rem 2rem;
        margin: 0.5rem 0 1rem;
    }
    .stat-grid .stat-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.7;
    }
    .stat-grid .stat-value {
        font-size: 1.1rem;
        font-weight: 500;
        margin-top: 0.15rem;
    }

    /* Buttons (colours from the theme's primary colour) */
    .stButton > button, .stFormSubmitButton > button {
        text-transform: uppercase;
        letter-spacing: 2px;
        transition: 0.3s all ease;
    }
    </style>
    """, unsafe_allow_html=True)

def format_number(value, is_market_cap=False):
    if value is None:
        return "N/A"
    
    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    if is_market_cap:
        if num >= 1e12:
            return f"${num / 1e12:.2f}T"
        if num >= 1e9:
            return f"${num / 1e9:.2f}B"
        if num >= 1e6:
            return f"${num / 1e6:.2f}M"
        return f"${num:,.2f}"

    # General number formatting (2 decimal places)
    return f"{num:.2f}"

# --- Cached data access ---
# Streamlit reruns the whole script on every interaction; caching stops each
# rerun from re-requesting Yahoo Finance and re-scraping the company website.

@st.cache_data(ttl=300, show_spinner="Fetching market data...")
def load_stock_data(ticker):
    data = get_stock_data(ticker)
    if data is None:
        # Raising (rather than returning None) means a failed lookup is not cached,
        # so a temporary network error doesn't stick for the whole TTL.
        raise LookupError(ticker)
    return data

@st.cache_data(ttl=60, show_spinner=False)
def load_latest_price(ticker):
    return get_live_price(ticker)

@st.cache_data(ttl=3600, show_spinner=False)
def load_website_summary(url):
    return scrape_company_website(url)


# --- AI research helpers ---

def get_gemini_settings():
    """Reads the Gemini API key and model from .streamlit/secrets.toml, falling back to env vars."""
    api_key = model = None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        model = st.secrets.get("GEMINI_MODEL")
    except Exception:  # no secrets.toml present
        pass
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    model = model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    return api_key, model

def escape_dollars(text):
    """Stops Streamlit Markdown from treating "$1.2B ... $3" as a LaTeX formula."""
    return text.replace("$", "\\$")

def render_grounded_result(result):
    """Shows one grounded answer as-is, with its sources and Google's Search Suggestions."""
    with st.container(border=True):
        st.markdown(escape_dollars(result.text))
    if result.sources:
        with st.expander(f"Sources ({len(result.sources)})"):
            for title, url in result.sources:
                safe_title = title.replace("[", "(").replace("]", ")")
                st.markdown(f"- [{escape_dollars(safe_title)}](<{url}>)")
    if result.search_suggestions_html:
        # Required by the Gemini grounding terms; iframed so Google's CSS can't clash with the app's.
        components.html(result.search_suggestions_html, height=110, scrolling=True)

# Session state for Navigation
if 'page' not in st.session_state:
    st.session_state.page = 'home'

def go_to_analysis(ticker):
    st.session_state.ticker = ticker
    st.session_state.page = 'analysis'

def go_home():
    st.session_state.page = 'home'

# --- HOME SCREEN ---
if st.session_state.page == 'home':
    st.markdown(
        "<div class='hero'><h1>Australian Stock Market Analyzer</h1>"
        "<p>Pure data. Refined insights.</p></div>",
        unsafe_allow_html=True,
    )
    
    # Sleek Search Bar
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        # Use a form to capture 'Enter' key presses
        with st.form(key='search_form', clear_on_submit=False):
            search_ticker = st.text_input("Ticker", placeholder="Enter Ticker (e.g. CBA or CBA.AX)", label_visibility="collapsed")
            submit_button = st.form_submit_button("Analyze")

        if submit_button:
            ticker = normalize_ticker(search_ticker)
            if not search_ticker or not search_ticker.strip():
                st.warning("Please enter a ticker.")
            elif ticker is None:
                st.warning("That doesn't look like a valid ticker. Use letters and numbers, e.g. CBA or BHP.AX.")
            else:
                go_to_analysis(ticker)
                st.rerun()  # render the analysis page now, not on the next interaction

# --- ANALYSIS SCREEN ---
elif st.session_state.page == 'analysis':
    ticker = st.session_state.get('ticker', '')
    
    if st.button("← Back to Search"):
        go_home()
        st.rerun()

    try:
        data = load_stock_data(ticker)
    except LookupError:
        data = None
    
    if data:
        info = data['info']
        history = data['history']
        news = data['news']
        
        # Header
        # Values come from an external API and are rendered as raw HTML, so escape them.
        company_name = html.escape(str(info.get('longName') or info.get('shortName') or ticker))
        sector = html.escape(str(info.get('sector', 'N/A')))
        industry = html.escape(str(info.get('industry', 'N/A')))
        st.markdown(f"<h1 class='company-title'>{company_name}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p class='company-subtitle'>{sector} — {industry}</p>", unsafe_allow_html=True)
        
        # Price & Metrics
        live_price = load_latest_price(ticker)
        m1, m2, m3, m4 = st.columns(4)
        
        # We use tooltips (help parameter) to show the full number on hover
        m1.metric("Price", f"${live_price:.2f}" if live_price else "N/A", help=f"Full Price: {live_price}")
        m2.metric("Market Cap", format_number(info.get('marketCap'), True), help=f"Full Value: {info.get('marketCap')}")
        m3.metric("P/E", format_number(info.get('trailingPE')), help=f"Full Value: {info.get('trailingPE')}")
        dividend_yield = get_dividend_yield_pct(info, live_price)
        m4.metric(
            "Yield",
            f"{dividend_yield:.2f}%" if dividend_yield is not None else "N/A",
            help=f"Annual dividend per share: {info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 'N/A'}",
        )


        # Charts
        st.markdown("---")
        tab1, tab2 = st.tabs(["Performance", "Volume"])
        chart_layout = dict(
            height=420,
            margin=dict(l=0, r=0, t=10, b=0),  # no title, so no empty space above the plot
            xaxis_title=None,
            yaxis_title=None,
            hovermode="x unified",
            showlegend=False,
        )
        with tab1:
            # Line only (no fill to zero): a fill forces the y-axis to start at $0,
            # which flattens the price movement the chart is meant to show.
            fig_price = go.Figure(go.Scatter(
                x=history.index, y=history['Close'], mode="lines",
                line=dict(width=2, color=CHART_GOLD),
                hovertemplate="$%{y:,.2f}<extra></extra>",
            ))
            fig_price.update_layout(**chart_layout, yaxis_tickprefix="$")
            st.plotly_chart(fig_price, width="stretch")
        with tab2:
            fig_vol = go.Figure(go.Bar(
                x=history.index, y=history['Volume'], marker_color=CHART_GOLD,
                hovertemplate="%{y:,.0f} shares<extra></extra>",
            ))
            fig_vol.update_layout(**chart_layout)
            st.plotly_chart(fig_vol, width="stretch")

        # Key statistics
        key_stats = build_key_stats(info)
        if key_stats:
            st.markdown("---")
            st.markdown("### Key Statistics")
            cells = "".join(
                f"<div><div class='stat-label'>{html.escape(label)}</div>"
                f"<div class='stat-value'>{html.escape(value)}</div></div>"
                for label, value in key_stats
            )
            st.markdown(f"<div class='stat-grid'>{cells}</div>", unsafe_allow_html=True)
            st.caption("Source: Yahoo Finance. Analyst figures are third-party opinions, not advice.")

        # AI research (Gemini + Google Search grounding)
        st.markdown("---")
        st.markdown("### AI Research")
        api_key, ai_model = get_gemini_settings()
        plain_name = info.get('longName') or info.get('shortName') or ticker
        # Kept per user session only: grounded results may not be cached or shared across users.
        research_store = st.session_state.setdefault("ai_research", {})

        if not api_key:
            st.info(
                "Add a Gemini API key to enable AI research: create `.streamlit/secrets.toml` "
                "containing `GEMINI_API_KEY = \"your-key\"`. See the README for details."
            )
        else:
            st.caption(
                f"Gemini searches the web and writes a company briefing plus a summary of news from the "
                f"last {NEWS_WINDOW_DAYS} days. Each run uses two Google-grounded Gemini requests."
            )
            button_label = "Regenerate AI research" if ticker in research_store else "Research this company with AI"
            if st.button(button_label, key="run_ai_research"):
                with st.spinner("Searching the web and writing the briefing. This can take a little while..."):
                    try:
                        research_store[ticker] = research_company(
                            api_key, plain_name, ticker,
                            sector=info.get('sector', ''), industry=info.get('industry', ''),
                            model=ai_model,
                        )
                    except ResearchError as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()  # redraw so the button reads "Regenerate"

        research = research_store.get(ticker)
        if research:
            st.caption(
                f"Generated {research.generated_at:%d %b %Y %H:%M} UTC by {research.model} using Google Search. "
                "AI-generated: it can be wrong or incomplete, so check the sources. Not financial advice."
            )
            tab_profile, tab_news = st.tabs([
                "Company briefing",
                f"News {research.news_start:%d %b} – {research.news_end:%d %b %Y}",
            ])
            with tab_profile:
                render_grounded_result(research.profile)
            with tab_news:
                render_grounded_result(research.news)

        # Detail Section
        st.markdown("---")
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("### Profile")
            st.markdown(escape_dollars(info.get('longBusinessSummary') or 'No summary available.'))
            
            website_url = info.get('website')
            if website_url:
                st.markdown(f"**Official Website:** [Link]({website_url})")
                with st.spinner("Fetching highlights..."):
                    st.info(load_website_summary(website_url))

        with col_right:
            st.markdown("### Latest Headlines")
            if news:
                for item in news[:5]:
                    title, link, publisher = parse_news_item(item)
                    st.markdown(f"**[{title}]({link})**" if link else f"**{title}**")
                    st.caption(publisher)
                    st.write("")
            else:
                st.write("No recent news found.")
    else:
        st.error(f"Couldn't load data for {ticker}. Check the ticker (ASX codes end in .AX) or try again in a moment.")
        if st.button("Return"):
            go_home()
            st.rerun()
