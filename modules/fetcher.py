import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

def get_stock_data(ticker_symbol):
    """
    Fetches comprehensive stock data and news for a given ticker symbol.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        news = stock.news
        hist = stock.history(period="1y")
        
        return {
            "info": info,
            "news": news,
            "history": hist
        }
    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")
        return None

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
