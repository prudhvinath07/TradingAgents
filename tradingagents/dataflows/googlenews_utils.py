import requests
import xml.etree.ElementTree as ET
import html
import re
from datetime import datetime
from urllib.parse import quote_plus


def getNewsData(query, start_date, end_date):
    """
    Fetch Google News results using the RSS feed API.
    Falls back to legacy HTML scraping if RSS fails.

    Args:
        query: str - search query (spaces can be + or literal)
        start_date: str - start date in yyyy-mm-dd or mm/dd/yyyy format
        end_date: str - end date in yyyy-mm-dd or mm/dd/yyyy format

    Returns:
        list of dicts with keys: link, title, snippet, date, source
    """
    # Normalize dates to yyyy-mm-dd for RSS after: / before: syntax
    start_str = _normalize_date(start_date)
    end_str = _normalize_date(end_date)

    # Normalize query (replace + with space for RSS URL encoding)
    clean_query = query.replace("+", " ").strip()

    results = _fetch_rss(clean_query, start_str, end_str)
    if results:
        return results

    # Fallback: try without date filters (sometimes yields more results)
    results = _fetch_rss(clean_query, None, None)
    if results:
        return results

    return []


def _normalize_date(date_str):
    """Convert date string to yyyy-mm-dd format."""
    date_str = str(date_str).strip()
    if "/" in date_str:
        dt = datetime.strptime(date_str, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    if "-" in date_str:
        # Already yyyy-mm-dd
        return date_str
    return date_str


def _fetch_rss(query, start_date=None, end_date=None):
    """
    Fetch news from Google News RSS feed.

    Args:
        query: search query string
        start_date: optional yyyy-mm-dd start date
        end_date: optional yyyy-mm-dd end date

    Returns:
        list of news item dicts
    """
    # Build query with date filters
    rss_query = query
    if start_date:
        rss_query += f" after:{start_date}"
    if end_date:
        rss_query += f" before:{end_date}"

    encoded_query = quote_plus(rss_query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/xml, text/xml, application/rss+xml",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Google News RSS returned status {response.status_code}")
            return []

        root = ET.fromstring(response.content)
        items = root.findall(".//item")

        if not items:
            return []

        news_results = []
        seen_titles = set()

        for item in items:
            title_elem = item.find("title")
            link_elem = item.find("link")
            pub_date_elem = item.find("pubDate")
            source_elem = item.find("source")
            desc_elem = item.find("description")

            title_raw = title_elem.text if title_elem is not None else ""
            if not title_raw:
                continue

            # Google News RSS titles often include " - Source Name" at the end
            title, source_from_title = _split_title_source(title_raw)

            source = ""
            if source_elem is not None and source_elem.text:
                source = source_elem.text
            elif source_from_title:
                source = source_from_title

            link = link_elem.text if link_elem is not None else ""
            pub_date = pub_date_elem.text if pub_date_elem is not None else ""

            # Extract snippet from description HTML
            snippet = ""
            if desc_elem is not None and desc_elem.text:
                snippet = re.sub(r"<[^>]+>", "", html.unescape(desc_elem.text)).strip()
                # Remove the title text if it appears in the snippet
                snippet = snippet.replace(title_raw, "").strip()
                snippet = snippet[:500]

            if title in seen_titles:
                continue
            seen_titles.add(title)

            news_results.append({
                "link": link,
                "title": title,
                "snippet": snippet if snippet else f"Source: {source}",
                "date": pub_date,
                "source": source,
            })

        return news_results

    except ET.ParseError as e:
        print(f"Failed to parse Google News RSS XML: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Google News RSS request failed: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error fetching Google News RSS: {e}")
        return []


def _split_title_source(title):
    """
    Split 'Article Title - Source Name' into (title, source).
    Google News RSS format: "Headline text - The Source"
    """
    # Split on last occurrence of " - "
    parts = title.rsplit(" - ", 1)
    if len(parts) == 2 and len(parts[1]) < 50:
        return parts[0].strip(), parts[1].strip()
    return title.strip(), ""
