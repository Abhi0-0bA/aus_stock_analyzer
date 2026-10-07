# aus_stock_analyzer

A minimalist Streamlit dashboard for Australian (ASX) stocks: latest price, key metrics and statistics, a 1-year price and volume chart, a company profile, recent headlines, and optional AI research (a company briefing plus a summary of the last 30 days of news) using Google Gemini with Google Search.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### AI research (optional)

1. Create a Gemini API key at https://aistudio.google.com/apikey.
2. Enable billing on that Google AI Studio project. Grounding with Google Search is not available on the free tier for current models. Check the [Gemini API pricing page](https://ai.google.dev/gemini-api/docs/pricing) for current rates, and consider setting a budget alert.
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your key. `secrets.toml` is git-ignored; never commit it.

Without a key, the rest of the dashboard works normally and the AI section shows these setup steps.

## Run

Web dashboard:

```bash
streamlit run app.py
```

Command-line report:

```bash
python main.py
```

Enter an ASX code such as `CBA` or `BHP.AX`. If you leave out the exchange suffix, `.AX` is added automatically.

## Light and dark mode

Both themes are defined in `.streamlit/config.toml`. Switch between System, Light and Dark from the ⋮ menu in the top-right corner. Keep colours in that file rather than in `app.py` CSS; hardcoded CSS colours are what previously broke dark mode.

Text and layout scale with the browser window (about 16px on laptops and phones, about 20px on a 2560px-wide screen).

## Project layout

- `app.py` – Streamlit UI, caching and navigation
- `modules/fetcher.py` – Yahoo Finance requests, ticker validation, company website summary
- `modules/analyzer.py` – news parsing, dividend yield, key statistics, text report
- `modules/ai_research.py` – Gemini research with Google Search grounding
- `.streamlit/config.toml` – light/dark theme and fonts

## Data notes

- Data comes from Yahoo Finance through `yfinance`, an unofficial library. It is intended for personal and research use, and it can break when Yahoo changes its responses; run `pip install -U yfinance` first if data stops loading.
- ASX prices from Yahoo are typically delayed, not real-time.
- Dividend yield is calculated as annual dividend per share ÷ price.
- AI research is generated from web search results and can be wrong or incomplete; check the linked sources. The news summary covers the most notable items Gemini finds in the last 30 days, not a complete archive. Nothing in this app is financial advice.
- Gemini's Google-grounded results are shown unmodified with Google's Search Suggestions, and are stored only in the current user's session, as the Gemini API terms require. Don't add a shared cache for them.
