"""
Direct Reddit API integration for TradingAgents.

Uses Reddit's public JSON API to fetch market sentiment without requiring MCP.
No authentication required for read-only public data.
"""

import requests
import json
from typing import Annotated
from datetime import datetime
import time
import random


# Financial/trading subreddits for market sentiment
TRADING_SUBREDDITS = [
    "wallstreetbets",      # Retail sentiment, meme stocks
    "stocks",              # General stock discussion
    "investing",           # Long-term investing
    "stockmarket",         # Market analysis
    "IndiaInvestments",    # Indian market (NSE/BSE)
    "IndianStreetBets",    # Indian retail traders
]


def _make_reddit_request(url: str) -> dict:
    """Make a request to Reddit's JSON API with rate limiting."""
    headers = {
        "User-Agent": "TradingAgents/1.0 (Market Research Bot)",
        "Accept": "application/json",
    }

    # Rate limiting - Reddit allows ~60 requests per minute
    time.sleep(random.uniform(1, 2))

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Reddit API error: {e}")
        return {"error": str(e)}


def _search_subreddit(subreddit: str, query: str, limit: int = 10, time_filter: str = "week") -> list:
    """Search a subreddit for posts matching query."""
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    url += f"?q={query}&restrict_sr=on&sort=relevance&t={time_filter}&limit={limit}"

    data = _make_reddit_request(url)

    if "error" in data:
        return []

    posts = []
    try:
        children = data.get("data", {}).get("children", [])
        for child in children:
            post_data = child.get("data", {})
            posts.append({
                "title": post_data.get("title", ""),
                "subreddit": post_data.get("subreddit", ""),
                "score": post_data.get("score", 0),
                "upvote_ratio": post_data.get("upvote_ratio", 0),
                "num_comments": post_data.get("num_comments", 0),
                "created_utc": post_data.get("created_utc", 0),
                "selftext": post_data.get("selftext", "")[:500],
                "url": post_data.get("url", ""),
                "permalink": f"https://reddit.com{post_data.get('permalink', '')}",
            })
    except Exception as e:
        print(f"Error parsing Reddit response: {e}")

    return posts


def _get_hot_posts(subreddit: str, limit: int = 10) -> list:
    """Get hot posts from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"

    data = _make_reddit_request(url)

    if "error" in data:
        return []

    posts = []
    try:
        children = data.get("data", {}).get("children", [])
        for child in children:
            post_data = child.get("data", {})
            # Skip stickied posts
            if post_data.get("stickied"):
                continue
            posts.append({
                "title": post_data.get("title", ""),
                "subreddit": post_data.get("subreddit", ""),
                "score": post_data.get("score", 0),
                "upvote_ratio": post_data.get("upvote_ratio", 0),
                "num_comments": post_data.get("num_comments", 0),
                "created_utc": post_data.get("created_utc", 0),
                "selftext": post_data.get("selftext", "")[:500],
                "url": post_data.get("url", ""),
                "permalink": f"https://reddit.com{post_data.get('permalink', '')}",
            })
    except Exception as e:
        print(f"Error parsing Reddit response: {e}")

    return posts


def _clean_ticker(ticker: str) -> str:
    """Remove exchange suffixes and clean ticker symbol."""
    suffixes = [".NS", ".BO", ".BSE", ".NSE", ".L", ".TO", ".AX", ".HK", ".T", ".SS", ".SZ"]
    clean = ticker.upper()
    for suffix in suffixes:
        if clean.endswith(suffix.upper()):
            clean = clean[:-len(suffix)]
            break
    return clean


def _get_search_terms(ticker: str) -> list:
    """Generate search terms for a ticker, including common variations."""
    clean_ticker = _clean_ticker(ticker)

    # ETF-specific terms
    etf_keywords = {
        "GOLDBEES": ["gold ETF", "gold", "GOLDBEES"],
        "SILVERBEES": ["silver ETF", "silver", "SILVERBEES"],
        "NIFTYBEES": ["nifty ETF", "nifty 50", "NIFTYBEES"],
        "BANKBEES": ["bank nifty ETF", "bank nifty", "BANKBEES"],
    }

    if clean_ticker in etf_keywords:
        return etf_keywords[clean_ticker]

    return [clean_ticker, f"${clean_ticker}"]


def get_reddit_stock_sentiment(
    ticker: Annotated[str, "Stock ticker symbol"],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of posts to return"] = 10,
) -> str:
    """
    Get Reddit sentiment for a specific stock ticker.
    Searches trading subreddits for mentions of the stock.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'GOLDBEES.NS')
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back
        limit: Maximum number of posts to return

    Returns:
        Formatted string with Reddit posts and sentiment
    """
    # Calculate time filter based on look_back_days
    if look_back_days <= 1:
        time_filter = "day"
    elif look_back_days <= 7:
        time_filter = "week"
    elif look_back_days <= 30:
        time_filter = "month"
    else:
        time_filter = "year"

    search_terms = _get_search_terms(ticker)
    all_posts = []
    seen_titles = set()

    # Determine which subreddits to search based on ticker
    clean_ticker = _clean_ticker(ticker)
    is_indian = ticker.endswith(".NS") or ticker.endswith(".BO") or clean_ticker in ["GOLDBEES", "SILVERBEES", "NIFTYBEES"]

    if is_indian:
        subreddits = ["IndiaInvestments", "IndianStreetBets", "stocks", "investing"]
    else:
        subreddits = TRADING_SUBREDDITS[:5]

    # Search for the ticker
    for search_term in search_terms:
        for subreddit in subreddits:
            posts = _search_subreddit(subreddit, search_term, limit=5, time_filter=time_filter)
            for post in posts:
                if post["title"] not in seen_titles:
                    seen_titles.add(post["title"])
                    all_posts.append(post)

            if len(all_posts) >= limit:
                break

        if len(all_posts) >= limit:
            break

    # Sort by score
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    all_posts = all_posts[:limit]

    if not all_posts:
        return f"[DATA UNAVAILABLE] No Reddit posts found for {ticker} in the past {look_back_days} days"

    # Format results
    result_str = f"## Reddit Sentiment: {ticker}\n"
    result_str += f"**Analysis Date:** {curr_date} | **Posts Found:** {len(all_posts)}\n\n"

    sentiment_indicators = {"bullish": 0, "bearish": 0, "neutral": 0}

    for i, post in enumerate(all_posts, 1):
        title = post["title"]
        subreddit = post["subreddit"]
        score = post["score"]
        comments = post["num_comments"]

        # Simple sentiment detection from title
        title_lower = title.lower()
        if any(word in title_lower for word in ["buy", "calls", "moon", "bullish", "long", "undervalued", "up", "gain", "profit"]):
            sentiment = "🟢 Bullish"
            sentiment_indicators["bullish"] += 1
        elif any(word in title_lower for word in ["sell", "puts", "crash", "bearish", "short", "overvalued", "down", "loss", "fall"]):
            sentiment = "🔴 Bearish"
            sentiment_indicators["bearish"] += 1
        else:
            sentiment = "⚪ Neutral"
            sentiment_indicators["neutral"] += 1

        result_str += (
            f"### {i}. {title}\n"
            f"**r/{subreddit}** | Score: {score} | Comments: {comments} | {sentiment}\n\n"
        )

    # Summary
    total = sum(sentiment_indicators.values())
    if total > 0:
        result_str += "\n---\n\n### Sentiment Summary\n"
        result_str += f"- 🟢 Bullish: {sentiment_indicators['bullish']} ({sentiment_indicators['bullish']*100//total}%)\n"
        result_str += f"- 🔴 Bearish: {sentiment_indicators['bearish']} ({sentiment_indicators['bearish']*100//total}%)\n"
        result_str += f"- ⚪ Neutral: {sentiment_indicators['neutral']} ({sentiment_indicators['neutral']*100//total}%)\n"

    return result_str


def get_reddit_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of posts to return"] = 10,
) -> str:
    """
    Get global market news and sentiment from Reddit.
    Browses financial subreddits for market-moving discussions.

    Args:
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back
        limit: Maximum number of posts to return

    Returns:
        Formatted string with Reddit posts about global markets
    """
    all_posts = []
    seen_titles = set()

    # Get hot posts from key financial subreddits
    for subreddit in ["wallstreetbets", "stocks", "economics", "investing"]:
        posts = _get_hot_posts(subreddit, limit=5)
        for post in posts:
            if post["title"] not in seen_titles:
                seen_titles.add(post["title"])
                all_posts.append(post)

        if len(all_posts) >= limit:
            break

    # Also search for market-moving topics
    market_queries = ["stock market", "economy", "Federal Reserve", "inflation"]
    for query in market_queries[:2]:
        posts = _search_subreddit("all", query, limit=3, time_filter="week")
        for post in posts:
            if post["title"] not in seen_titles and post["score"] > 50:
                seen_titles.add(post["title"])
                all_posts.append(post)

    # Sort by score
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    all_posts = all_posts[:limit]

    if not all_posts:
        return f"[DATA UNAVAILABLE] No Reddit posts found for global market news"

    # Format results
    result_str = "## Reddit Global Market Sentiment\n"
    result_str += f"**Analysis Date:** {curr_date} | **Posts Found:** {len(all_posts)}\n\n"

    for i, post in enumerate(all_posts, 1):
        title = post["title"]
        subreddit = post["subreddit"]
        score = post["score"]
        comments = post["num_comments"]

        result_str += (
            f"### {i}. {title}\n"
            f"**r/{subreddit}** | Score: {score} | Comments: {comments}\n\n"
        )

    return result_str
