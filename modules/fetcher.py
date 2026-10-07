import re

import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Letters/digits plus the separators Yahoo uses (".AX" suffix, "^AXJO" indices, "-" share classes).
_TICKER_PATTERN = re.compile(r"^\^?[A-Z0-9][A-Z0-9.\-]{0,14}$")


def normalize_ticker(raw_ticker):
    """
    Cleans user input into a Yahoo Finance ticker.

    Returns the ticker in upper case, adding the ASX suffix ".AX" when no
    exchange suffix is given (e.g. "cba" -> "CBA.AX"). Index symbols that
    start with "^" are left as they are. Returns None for invalid input.
    """
    if not raw_ticker:
        return None
    ticker = raw_ticker.strip().upper()
    if not _TICKER_PATTERN.match(ticker):
        return None
    if "." not in ticker and not ticker.startswith("^"):
        ticker += ".AX"
    return ticker


def get_stock_data(ticker_symbol):
    """
    Fetches comprehensive stock data and news for a given ticker symbol.

    Returns None when the ticker has no price history (unknown or delisted
    ticker) or the price request fails. Missing info or news does not fail
    the whole lookup.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        hist = stock.history(period="1y")
    except Exception as e:
        print(f"Error fetching price history for {ticker_symbol}: {e}")
        return None

    # yfinance usually returns an empty frame (not an exception) for unknown tickers.
    if hist is None or hist.empty:
        print(f"No price history found for {ticker_symbol}")
        return None

    try:
        info = stock.info or {}
    except Exception as e:
        print(f"Error fetching info for {ticker_symbol}: {e}")
        info = {}

    try:
        news = stock.news or []
    except Exception as e:
        print(f"Error fetching news for {ticker_symbol}: {e}")
        news = []

    return {
        "info": info,
        "news": news,
        "history": hist
    }

def get_live_price(ticker_symbol):
    """
    Fetches only the latest price for live updates.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        return stock.fast_info['last_price']
    except Exception as e:
        print(f"Error fetching live price for {ticker_symbol}: {e}")
        return None

def scrape_company_website(url):
    """
    Fetches the company website and extracts basic summary information.
    """
    if not url:
        return "No website URL available."
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text from paragraphs and headers to get a general idea
        paragraphs = soup.find_all('p')
        text_content = " ".join([p.text for p in paragraphs[:5]]) # Get first 5 paragraphs
        
        if len(text_content) < 50:
            return "Could not extract significant information from the website."
            
        return text_content[:1000] + "..." # Return a snippet
    except Exception as e:
        return f"Unable to scrape website: {e}"
