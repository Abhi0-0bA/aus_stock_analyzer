import streamlit as st
import plotly.graph_objects as go
from modules.fetcher import get_stock_data, get_live_price, scrape_company_website

st.set_page_config(
    page_title="Australian Stock Market Analyzer", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Luxury Minimalist Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;600&display=swap');

    :root {
        --luxury-black: #1a1a1a;
        --luxury-gold: #c5a059;
        --luxury-white: #ffffff;
        --luxury-gray: #fcfcfc;
    }

    /* Responsive Font Scaling and Luxury Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--luxury-black);
    }

    h1, h2, h3, .stTitle {
        font-family: 'Playfair Display', serif !important;
        font-weight: 700 !important;
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

    /* Minimalist Theme Logic */
    .stApp {
        background-color: var(--luxury-gray) !important;
    }

    /* Dark Mode Fix: Ensure contrast is maintained */
    [data-testid="stAppViewContainer"] {
        background-color: var(--luxury-gray) !important;
    }

    /* Luxury Search Bar */
    .search-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 100px 0;
    }

    /* Card styling - Minimalist */
    [data-testid="stMetric"] {
        background: transparent !important;
        border-bottom: 1px solid #ddd !important;
        box-shadow: none !important;
        padding: 10px 0 !important;
    }

    /* Button Luxury Style */
    .stButton > button {
        border-radius: 0px !important;
        background-color: var(--luxury-black) !important;
        color: white !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-family: 'Inter', sans-serif !important;
        border: none !important;
        transition: 0.3s all ease;
    }
    
    .stButton > button:hover {
        background-color: var(--luxury-gold) !important;
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
            search_ticker = st.text_input("", placeholder="Enter Ticker (e.g. CBA.AX)", label_visibility="collapsed")
            submit_button = st.form_submit_button("Analyze")
            
        if submit_button and search_ticker:
            go_to_analysis(search_ticker.strip().upper())
        elif submit_button and not search_ticker:
            st.warning("Please enter a ticker.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- ANALYSIS SCREEN ---
elif st.session_state.page == 'analysis':
    ticker = st.session_state.get('ticker', '')
    
    if st.button("← Back to Search"):
        go_home()
        st.rerun()

    data = get_stock_data(ticker)
    
    if data:
        info = data['info']
        history = data['history']
        news = data['news']
        
        # Header
        st.markdown(f"<h1 style='font-size: 3rem;'>{info.get('longName', 'Unknown')}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 1.2rem; color: gray;'>{info.get('sector', 'N/A')} — {info.get('industry', 'N/A')}</p>", unsafe_allow_html=True)
        
        # Price & Metrics
        live_price = get_live_price(ticker)
        m1, m2, m3, m4 = st.columns(4)
        
        # We use tooltips (help parameter) to show the full number on hover
        m1.metric("Price", f"${live_price:.2f}" if live_price else "N/A", help=f"Full Price: {live_price}")
        m2.metric("Market Cap", format_number(info.get('marketCap'), True), help=f"Full Value: {info.get('marketCap')}")
        m3.metric("P/E", format_number(info.get('trailingPE')), help=f"Full Value: {info.get('trailingPE')}")
        m4.metric("Yield", f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "N/A", help=f"Full Value: {info.get('dividendYield')}")


        # Charts
        st.markdown("---")
        tab1, tab2 = st.tabs(["Performance", "Volume"])
        with tab1:
            fig_price = go.Figure(go.Scatter(x=history.index, y=history['Close'], line=dict(color='#1a1a1a', width=2), fill='tozeroy'))
            fig_price.update_layout(template="plotly_white", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_price, use_container_width=True)
        with tab2:
            fig_vol = go.Figure(go.Bar(x=history.index, y=history['Volume'], marker_color='#ddd'))
            fig_vol.update_layout(template="plotly_white", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
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
                    st.info(scrape_company_website(website_url))

        with col_right:
            st.markdown("### News")
            if news:
                for item in news[:5]:
                    sentiment = "Positive" if any(word in item['title'].lower() for word in ['growth', 'rise', 'profit']) else "Neutral"
                    st.markdown(f"**[{item['title']}]({item['link']})**")
                    st.caption(f"{item.get('publisher', 'Unknown')} | {sentiment}")
                    st.write("")
            else:
                st.write("No recent news found.")
    else:
        st.error("Ticker not found.")
        if st.button("Return"):
            go_home()
            st.rerun()
