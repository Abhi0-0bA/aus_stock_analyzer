import html

import streamlit as st
import plotly.graph_objects as go
from modules.fetcher import get_stock_data, get_live_price, scrape_company_website, normalize_ticker
from modules.analyzer import parse_news_item, get_dividend_yield_pct

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
    h1, h2, h3 {
        letter-spacing: -0.02em !important;
    }

    /* Dynamic Text Scaling based on viewport */
    .stMarkdown p {
        font-size: clamp(1.5rem, 2vw, 2rem) !important;
        line-height: 1.6 !important;
    }

    .stMetric {
        font-size: clamp(2rem, 3vw, 3rem) !important;
    }

    /* Luxury Search Bar */
    .search-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 100px 0;
    }

    /* Card styling - Minimalist (translucent grey border works on light and dark) */
    [data-testid="stMetric"] {
        background: transparent !important;
        border-bottom: 1px solid rgba(128, 128, 128, 0.3) !important;
        box-shadow: none !important;
        padding: 10px 0 !important;
    }

    /* Button Luxury Style (colours from the theme's primary colour) */
    .stButton > button, .stFormSubmitButton > button {
        text-transform: uppercase;
        letter-spacing: 2px;
        transition: 0.3s all ease;
    }

    /* Resolution Scaling for Layout */
    .block-container {
        max-width: 1200px !important;
        padding: 3rem !important;
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
    st.markdown("<div class='search-container'>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 4rem; margin-bottom: 1rem;'>Australian Stock Market Analyzer</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.5rem; font-weight: 300; margin-bottom: 3rem;'>Pure data. Refined insights.</p>", unsafe_allow_html=True)
    
    # Sleek Search Bar
    col1, col2, col3 = st.columns([1, 2, 1])
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
    st.markdown("</div>", unsafe_allow_html=True)

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
        st.markdown(f"<h1 style='font-size: 3rem;'>{company_name}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 1.2rem; opacity: 0.7;'>{sector} — {industry}</p>", unsafe_allow_html=True)
        
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
        with tab1:
            fig_price = go.Figure(go.Scatter(x=history.index, y=history['Close'], line=dict(width=2, color=CHART_GOLD), fill='tozeroy'))
            fig_price.update_layout(xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_price, use_container_width=True)
        with tab2:
            fig_vol = go.Figure(go.Bar(x=history.index, y=history['Volume'], marker_color=CHART_GOLD))
            fig_vol.update_layout(xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_vol, use_container_width=True)

        # Detail Section
        st.markdown("---")
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("### Profile")
            st.write(info.get('longBusinessSummary', 'No summary available.'))
            
            website_url = info.get('website')
            if website_url:
                st.markdown(f"**Official Website:** [Link]({website_url})")
                with st.spinner("Fetching highlights..."):
                    st.info(load_website_summary(website_url))

        with col_right:
            st.markdown("### News")
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
