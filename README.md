# aus_stock_analyzer

A minimalist Streamlit dashboard for Australian (ASX) stocks: latest price, key metrics, a 1-year price and volume chart, a company profile and recent news, using Yahoo Finance data via `yfinance`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

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

## Project layout

- `app.py` – Streamlit UI, caching and navigation
- `modules/fetcher.py` – Yahoo Finance requests, ticker validation, company website summary
- `modules/analyzer.py` – news parsing, dividend yield calculation, text report

## Data notes

- Data comes from Yahoo Finance through `yfinance`, an unofficial library. It is intended for personal and research use, and it can break when Yahoo changes its responses; run `pip install -U yfinance` first if data stops loading.
- ASX prices from Yahoo are typically delayed, not real-time.
- Dividend yield is calculated as annual dividend per share ÷ price.
