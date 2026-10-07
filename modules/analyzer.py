def format_news(news_list):
    """
    Formats the raw news list into a readable string.
    """
    if not news_list:
        return "No recent news found."
    
    formatted_news = []
    for idx, item in enumerate(news_list[:5], 1):
        title = item.get('title', 'No Title')
        link = item.get('link', 'No Link')
        publisher = item.get('publisher', 'Unknown')
        formatted_news.append(f"{idx}. {title} (by {publisher})\n   Link: {link}")
    
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
    report.append(f"Dividend Yield: {info.get('dividendYield', 'N/A')}")
    
    report.append(f"\n--- Latest News ---")
    report.append(format_news(news))
    
    return "\n".join(report)
