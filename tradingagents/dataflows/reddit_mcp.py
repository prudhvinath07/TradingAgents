"""
Reddit MCP Integration for TradingAgents.

Uses the reddit-mcp-buddy MCP server to fetch market sentiment from Reddit.
Requires the reddit-mcp-buddy MCP server to be configured and running.

Setup:
1. Install: claude mcp add reddit-mcp-buddy -- npx -y reddit-mcp-buddy
2. Configure Reddit API credentials (optional but recommended):
   - REDDIT_CLIENT_ID
   - REDDIT_CLIENT_SECRET
   - REDDIT_USERNAME
   - REDDIT_PASSWORD
"""

import subprocess
import json
import os
from typing import Annotated
from datetime import datetime
from dateutil.relativedelta import relativedelta


# Financial/trading subreddits for market sentiment
TRADING_SUBREDDITS = [
    "wallstreetbets",      # Retail sentiment, meme stocks
    "stocks",              # General stock discussion
    "investing",           # Long-term investing
    "stockmarket",         # Market analysis
    "options",             # Options trading
    "IndiaInvestments",    # Indian market (NSE/BSE)
    "IndianStreetBets",    # Indian retail traders
]

# Global market/economy subreddits
GLOBAL_NEWS_SUBREDDITS = [
    "economics",           # Economic news and analysis
    "finance",             # Finance news
    "worldnews",           # Global news (filter for financial)
    "business",            # Business news
]

# MCP CLI paths to try
MCP_CLI_PATHS = [
    "mcp-cli",  # If in PATH
    os.path.expanduser("~/.claude/local/node_modules/@anthropic-ai/claude-code/cli.js"),
]


def _get_mcp_cli_command():
    """Get the mcp-cli command, trying various paths."""
    # First try direct mcp-cli
    for path in MCP_CLI_PATHS:
        try:
            if path == "mcp-cli":
                # Check if command exists
                result = subprocess.run(
                    ["which", "mcp-cli"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return ["mcp-cli"]
            elif os.path.exists(path):
                return ["node", path, "--mcp-cli"]
        except Exception:
            continue

    return None


def _call_mcp_tool(tool_name: str, params: dict) -> dict:
    """
    Call a reddit-mcp-buddy MCP tool using mcp-cli.

    Args:
        tool_name: Name of the tool (e.g., 'search_reddit', 'browse_subreddit')
        params: Parameters to pass to the tool

    Returns:
        Parsed JSON response from the tool
    """
    try:
        mcp_cmd = _get_mcp_cli_command()
        if not mcp_cmd:
            return {"error": "mcp-cli not found. Please ensure Claude Code CLI is installed."}

        cmd = mcp_cmd + [
            "call",
            f"reddit-mcp-buddy/{tool_name}",
            json.dumps(params)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"MCP call failed: {result.stderr}")
            return {"error": result.stderr}

        # Parse the JSON response
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            # Response might be plain text
            return {"result": result.stdout}

    except subprocess.TimeoutExpired:
        return {"error": "MCP call timed out"}
    except FileNotFoundError:
        return {"error": "mcp-cli not found. Please ensure MCP CLI is installed."}
    except Exception as e:
        return {"error": str(e)}


def _check_mcp_available() -> bool:
    """Check if reddit-mcp-buddy MCP server is available."""
    try:
        mcp_cmd = _get_mcp_cli_command()
        if not mcp_cmd:
            return False

        result = subprocess.run(
            mcp_cmd + ["tools", "reddit-mcp-buddy"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0 and "search_reddit" in result.stdout
    except Exception:
        return False


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
        ticker: Stock ticker symbol (e.g., 'AAPL', 'ITC')
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back
        limit: Maximum number of posts to return

    Returns:
        Formatted string with Reddit posts and sentiment
    """
    # Clean ticker for search
    clean_ticker = ticker.upper().replace(".NS", "").replace(".BO", "")

    # Calculate time filter based on look_back_days
    if look_back_days <= 1:
        time_filter = "day"
    elif look_back_days <= 7:
        time_filter = "week"
    elif look_back_days <= 30:
        time_filter = "month"
    else:
        time_filter = "year"

    # Search for the ticker in trading subreddits
    params = {
        "query": clean_ticker,
        "subreddits": TRADING_SUBREDDITS[:5],  # Limit to top 5 subreddits
        "sort": "relevance",
        "time": time_filter,
        "limit": limit
    }

    response = _call_mcp_tool("search_reddit", params)

    if "error" in response:
        return f"[DATA UNAVAILABLE] Reddit MCP error: {response['error']}"

    # Parse and format results
    return _format_reddit_results(response, clean_ticker, curr_date, "Stock Sentiment")


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
    # Calculate time filter
    if look_back_days <= 1:
        time_filter = "day"
    elif look_back_days <= 7:
        time_filter = "week"
    elif look_back_days <= 30:
        time_filter = "month"
    else:
        time_filter = "year"

    all_posts = []
    posts_per_subreddit = max(2, limit // len(GLOBAL_NEWS_SUBREDDITS))

    # Search for market-related terms
    market_queries = [
        "stock market",
        "economy",
        "Federal Reserve",
        "inflation",
        "recession",
    ]

    # Try searching first
    for query in market_queries[:3]:
        params = {
            "query": query,
            "subreddits": GLOBAL_NEWS_SUBREDDITS,
            "sort": "top",
            "time": time_filter,
            "limit": posts_per_subreddit
        }

        response = _call_mcp_tool("search_reddit", params)

        if "error" not in response and "result" in response:
            posts = _extract_posts(response)
            all_posts.extend(posts)

        if len(all_posts) >= limit:
            break

    # Also browse top posts from key subreddits
    if len(all_posts) < limit:
        for subreddit in ["wallstreetbets", "stocks", "economics"][:2]:
            params = {
                "subreddit": subreddit,
                "sort": "hot",
                "time": time_filter,
                "limit": posts_per_subreddit
            }

            response = _call_mcp_tool("browse_subreddit", params)

            if "error" not in response:
                posts = _extract_posts(response)
                all_posts.extend(posts)

            if len(all_posts) >= limit:
                break

    if not all_posts:
        return f"[DATA UNAVAILABLE] No Reddit posts found for global market news"

    # Format results
    return _format_global_results(all_posts[:limit], curr_date)


def _extract_posts(response: dict) -> list:
    """Extract posts from MCP response."""
    posts = []

    if isinstance(response, dict):
        # Handle different response formats
        if "result" in response:
            result = response["result"]
            if isinstance(result, str):
                # Try to parse as JSON
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    return posts

            if isinstance(result, dict) and "posts" in result:
                posts = result["posts"]
            elif isinstance(result, list):
                posts = result

    return posts


def _format_reddit_results(response: dict, ticker: str, curr_date: str, context: str) -> str:
    """Format Reddit search results into a readable string."""
    posts = _extract_posts(response)

    if not posts:
        return f"[DATA UNAVAILABLE] No Reddit posts found for {ticker}"

    result_str = f"## Reddit {context}: {ticker}\n"
    result_str += f"**Analysis Date:** {curr_date} | **Posts Found:** {len(posts)}\n\n"

    sentiment_indicators = {"bullish": 0, "bearish": 0, "neutral": 0}

    for i, post in enumerate(posts[:10], 1):
        title = post.get("title", "No title")
        subreddit = post.get("subreddit", "unknown")
        score = post.get("score", 0)
        comments = post.get("num_comments", 0)

        # Simple sentiment detection from title
        title_lower = title.lower()
        if any(word in title_lower for word in ["buy", "calls", "moon", "bullish", "long", "undervalued"]):
            sentiment = "🟢 Bullish"
            sentiment_indicators["bullish"] += 1
        elif any(word in title_lower for word in ["sell", "puts", "crash", "bearish", "short", "overvalued"]):
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


def _format_global_results(posts: list, curr_date: str) -> str:
    """Format global news posts into a readable string."""
    if not posts:
        return "[DATA UNAVAILABLE] No Reddit posts found for global market news"

    result_str = "## Reddit Global Market Sentiment\n"
    result_str += f"**Analysis Date:** {curr_date} | **Posts Found:** {len(posts)}\n\n"

    for i, post in enumerate(posts[:10], 1):
        title = post.get("title", "No title")
        subreddit = post.get("subreddit", "unknown")
        score = post.get("score", 0)
        comments = post.get("num_comments", 0)

        result_str += (
            f"### {i}. {title}\n"
            f"**r/{subreddit}** | Score: {score} | Comments: {comments}\n\n"
        )

    return result_str
