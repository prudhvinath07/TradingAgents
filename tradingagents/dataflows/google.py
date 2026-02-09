from typing import Annotated
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .googlenews_utils import getNewsData
import yfinance as yf

# Cache for company names to avoid repeated API calls
_company_name_cache = {}


def _get_company_name(ticker: str) -> str:
    """
    Get company name from yfinance for a given ticker symbol.
    Caches results to avoid repeated API calls.
    """
    if ticker in _company_name_cache:
        return _company_name_cache[ticker]

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        # Try shortName first, then longName
        company_name = info.get('shortName') or info.get('longName') or None
        if company_name:
            _company_name_cache[ticker] = company_name
            return company_name
    except Exception as e:
        print(f"Could not fetch company name for {ticker}: {e}")

    return None


def _clean_ticker(ticker: str) -> str:
    """Remove exchange suffixes and clean ticker symbol."""
    suffixes = [".NS", ".BO", ".BSE", ".NSE", ".L", ".TO", ".AX", ".HK", ".T", ".SS", ".SZ"]
    clean = ticker.upper()
    for suffix in suffixes:
        if clean.endswith(suffix.upper()):
            clean = clean[:-len(suffix)]
            break
    return clean


def _get_search_queries(ticker: str) -> list:
    """
    Generate multiple search queries for better news coverage.
    Uses yfinance to get company name dynamically.
    Handles ETFs specially by extracting underlying asset terms.
    """
    # Try to get company name from yfinance
    company_name = _get_company_name(ticker)

    # Also try without exchange suffix if original failed
    if not company_name:
        clean_ticker = _clean_ticker(ticker)
        # Try adding common suffixes
        for suffix in [".NS", ".BO", ""]:
            test_ticker = clean_ticker + suffix
            company_name = _get_company_name(test_ticker)
            if company_name:
                break

    clean_ticker = _clean_ticker(ticker)
    queries = []

    # Check if this is an ETF and extract underlying asset
    name_upper = (company_name or '').upper()
    is_etf = 'ETF' in name_upper or 'BEES' in name_upper

    if is_etf:
        # Extract underlying asset from ETF name for better news coverage
        # e.g., "Nippon India ETF Gold BeES" -> search for "gold ETF india"
        underlying_assets = []

        # Common ETF underlying assets
        asset_keywords = {
            'GOLD': ['gold ETF india', 'gold price india'],
            'SILVER': ['silver ETF india', 'silver price india'],
            'NIFTY': ['nifty 50 ETF', 'nifty index fund'],
            'SENSEX': ['sensex ETF', 'BSE index fund'],
            'BANK': ['bank nifty ETF', 'banking sector india'],
            'IT': ['IT sector india', 'nifty IT ETF'],
            'LIQUID': ['liquid ETF india', 'money market fund'],
            'JUNIOR': ['nifty next 50 ETF', 'nifty junior'],
        }

        for keyword, search_terms in asset_keywords.items():
            if keyword in name_upper or keyword in clean_ticker.upper():
                underlying_assets.extend(search_terms)
                break

        if underlying_assets:
            queries.extend(underlying_assets)

        # Also add the ETF name variations
        if company_name:
            queries.append(f"{company_name}")

    else:
        # Regular stock
        if company_name:
            # Primary: Company name + stock
            queries.append(f"{company_name} stock")
            # Secondary: Just company name
            queries.append(company_name)

    # Fallback: Clean ticker + stock
    queries.append(f"{clean_ticker} stock")
    queries.append(clean_ticker)

    return queries


def get_google_news(
    query: Annotated[str, "Query to search with (ticker symbol)"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Scrape Google News for a given query and date range.
    Automatically converts ticker symbols to company names for better results.

    Args:
        query: Search query (typically ticker symbol)
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format

    Returns:
        Formatted string with news results
    """
    original_query = query

    # Get optimized search queries
    search_queries = _get_search_queries(query)

    all_news_results = []
    successful_query = None

    # Try each query until we get results
    for search_query in search_queries:
        search_query_encoded = search_query.replace(" ", "+")
        news_results = getNewsData(search_query_encoded, start_date, end_date)

        if news_results:
            all_news_results = news_results
            successful_query = search_query
            break

    if not all_news_results:
        clean_ticker = _clean_ticker(original_query)
        tried_queries = ", ".join(f"'{q}'" for q in search_queries[:3])
        return f"No Google News results found for {clean_ticker} (tried: {tried_queries}) between {start_date} and {end_date}"

    news_str = ""
    for news in all_news_results:
        news_str += (
            f"### {news['title']} (source: {news['source']}) \n\n{news['snippet']}\n\n"
        )

    clean_ticker = _clean_ticker(original_query)
    return f"## {clean_ticker} News (via '{successful_query}'), from {start_date} to {end_date}:\n\n{news_str}"


def get_google_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 10,
) -> str:
    """
    Fetch global financial and market news from Google News.
    Searches multiple financial topics to get comprehensive market coverage.

    Args:
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back (default 7)
        limit: Maximum number of articles to return (default 10)

    Returns:
        Formatted string with global news results
    """
    # Calculate date range
    end_date = curr_date
    start_date_dt = datetime.strptime(curr_date, "%Y-%m-%d") - relativedelta(days=look_back_days)
    start_date = start_date_dt.strftime("%Y-%m-%d")

    # Global financial news search queries
    global_queries = [
        "stock market today",
        "global economy news",
        "Federal Reserve interest rates",
        "inflation economic news",
        "S&P 500 Nasdaq market",
        "oil prices commodities",
        "cryptocurrency bitcoin market",
        "India NSE BSE market",
    ]

    all_news_results = []
    articles_per_query = max(2, limit // len(global_queries))

    for query in global_queries:
        try:
            query_encoded = query.replace(" ", "+")
            news_results = getNewsData(query_encoded, start_date, end_date)

            # Take limited articles per query to ensure diversity
            for news in news_results[:articles_per_query]:
                # Avoid duplicates by checking titles
                if not any(news['title'] == existing['title'] for existing in all_news_results):
                    news['query_source'] = query
                    all_news_results.append(news)

            # Stop if we have enough articles
            if len(all_news_results) >= limit:
                break

        except Exception as e:
            print(f"Error fetching global news for '{query}': {e}")
            continue

    if not all_news_results:
        return f"[DATA UNAVAILABLE] No global news results found between {start_date} and {end_date}"

    # Format the results
    news_str = ""
    for news in all_news_results[:limit]:
        query_tag = news.get('query_source', 'general')
        news_str += (
            f"### {news['title']}\n"
            f"**Source:** {news['source']} | **Topic:** {query_tag}\n\n"
            f"{news['snippet']}\n\n---\n\n"
        )

    return (
        f"## Global Market & Financial News\n"
        f"**Period:** {start_date} to {end_date} | **Articles:** {len(all_news_results[:limit])}\n\n"
        f"{news_str}"
    )