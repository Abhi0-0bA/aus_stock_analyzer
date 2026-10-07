from modules.fetcher import get_stock_data
from modules.analyzer import generate_report

def main():
    print("--- Australian Stock Market Analyzer ---")
    ticker = input("Enter Australian Stock Ticker (e.g., CBA.AX, BHP.AX): ").strip().upper()
    
    if not ticker:
        print("Invalid ticker. Exiting.")
        return

    print(f"\nFetching data for {ticker}...")
    data = get_stock_data(ticker)
    
    if data:
        report = generate_report(data)
        print("\n" + report)
    else:
        print("Could not retrieve data for the specified ticker.")

if __name__ == "__main__":
    main()
