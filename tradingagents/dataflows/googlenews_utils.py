import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
import re
from urllib.parse import unquote, urlparse, parse_qs
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_result,
)


def is_rate_limited(response):
    """Check if the response indicates rate limiting (status code 429)"""
    return response.status_code == 429


@retry(
    retry=(retry_if_result(is_rate_limited)),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
)
def make_request(url, headers):
    """Make a request with retry logic for rate limiting"""
    # Random delay before each request to avoid detection
    time.sleep(random.uniform(1, 3))
    response = requests.get(url, headers=headers, timeout=15)
    return response


def _extract_real_url(google_url):
    """Extract the real URL from Google's redirect URL."""
    if not google_url:
        return None
    if google_url.startswith('/url?'):
        # Parse the Google redirect URL
        parsed = urlparse(google_url)
        params = parse_qs(parsed.query)
        if 'q' in params:
            return params['q'][0]
        if 'url' in params:
            return params['url'][0]
    return google_url


def _parse_news_item_method1(el):
    """Parse news item using original selectors (div.SoaBEf structure)."""
    try:
        link = el.find("a")["href"]
        title = el.select_one("div.MBeuO").get_text()
        snippet = el.select_one(".GI74Re").get_text()
        date = el.select_one(".LfVVr").get_text()
        source = el.select_one(".NUnG9d span").get_text()
        return {
            "link": _extract_real_url(link) or link,
            "title": title,
            "snippet": snippet,
            "date": date,
            "source": source,
        }
    except Exception:
        return None


def _parse_news_item_method2(el):
    """Parse news item using alternative selectors (div.Gx5Zad structure)."""
    try:
        link_elem = el.find("a", href=True)
        if not link_elem:
            return None
        link = link_elem["href"]

        # Try multiple title selectors
        title = None
        for sel in ["div.BNeawe.vvjwJb", "h3", "div.n0jPhd"]:
            title_elem = el.select_one(sel)
            if title_elem:
                title = title_elem.get_text(strip=True)
                break

        if not title:
            return None

        # Try multiple snippet selectors
        snippet = ""
        for sel in ["div.BNeawe.s3v9rd", ".VwiC3b", ".Y3v8qd"]:
            snippet_elem = el.select_one(sel)
            if snippet_elem:
                snippet = snippet_elem.get_text(strip=True)
                break

        # Source is often at the beginning of the snippet or in a separate element
        source = "Unknown"
        source_elem = el.select_one(".CEMjEf span") or el.select_one(".UPmit")
        if source_elem:
            source = source_elem.get_text(strip=True)

        return {
            "link": _extract_real_url(link) or link,
            "title": title,
            "snippet": snippet[:500] if snippet else "",
            "date": "",
            "source": source,
        }
    except Exception:
        return None


def _parse_news_from_divs(soup):
    """
    Fallback method: Find news articles by looking for div structures
    that contain links to external news sites.
    """
    news_results = []
    seen_titles = set()

    # Look for divs that contain anchor tags pointing to news articles
    for div in soup.find_all('div'):
        # Skip if too small or too large
        text = div.get_text(strip=True)
        if len(text) < 50 or len(text) > 2000:
            continue

        # Find the first anchor with an external link
        link_elem = div.find('a', href=True)
        if not link_elem:
            continue

        href = link_elem.get('href', '')
        real_url = _extract_real_url(href)

        # Skip if not a news link
        if not real_url or 'google.com' in real_url:
            continue

        # Extract title from the link text or nearby elements
        title = link_elem.get_text(strip=True)
        if len(title) < 10:
            # Try to find a better title
            h3 = div.find('h3')
            if h3:
                title = h3.get_text(strip=True)

        if len(title) < 10 or title in seen_titles:
            continue

        seen_titles.add(title)

        # Extract snippet (text after title)
        full_text = text
        snippet = full_text.replace(title, '').strip()[:500]

        # Try to extract source from URL or text
        source = "Unknown"
        try:
            parsed_url = urlparse(real_url)
            source = parsed_url.netloc.replace('www.', '')
        except Exception:
            pass

        # Look for source name patterns like "Source Name · date"
        source_match = re.search(r'^([A-Za-z0-9\s]+)\s*[·•]\s*', snippet)
        if source_match:
            source = source_match.group(1).strip()
            snippet = snippet[source_match.end():].strip()

        news_results.append({
            "link": real_url,
            "title": title,
            "snippet": snippet,
            "date": "",
            "source": source,
        })

        # Limit to avoid duplicates
        if len(news_results) >= 20:
            break

    return news_results


def getNewsData(query, start_date, end_date):
    """
    Scrape Google News search results for a given query and date range.
    Uses multiple parsing strategies to handle Google's changing HTML structure.

    Args:
        query: str - search query (use + for spaces)
        start_date: str - start date in the format yyyy-mm-dd or mm/dd/yyyy
        end_date: str - end date in the format yyyy-mm-dd or mm/dd/yyyy

    Returns:
        list of dicts with keys: link, title, snippet, date, source
    """
    # Convert date format if needed
    if "-" in str(start_date):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start_date = start_date.strftime("%m/%d/%Y")
    if "-" in str(end_date):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        end_date = end_date.strftime("%m/%d/%Y")

    # Use a more modern User-Agent
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    news_results = []
    page = 0
    max_pages = 3  # Limit pagination to avoid rate limiting

    while page < max_pages:
        offset = page * 10
        url = (
            f"https://www.google.com/search?q={query}"
            f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
            f"&tbm=nws&start={offset}"
        )

        try:
            response = make_request(url, headers)
            if response.status_code != 200:
                print(f"Google News request failed with status {response.status_code}")
                break

            soup = BeautifulSoup(response.content, "html.parser")

            # Try Method 1: Original selectors (div.SoaBEf)
            results_on_page = soup.select("div.SoaBEf")
            for el in results_on_page:
                item = _parse_news_item_method1(el)
                if item:
                    news_results.append(item)

            # Try Method 2: Alternative selectors (div.Gx5Zad)
            if not results_on_page:
                results_on_page = soup.select("div.Gx5Zad")
                for el in results_on_page:
                    item = _parse_news_item_method2(el)
                    if item and item['title'] not in [r['title'] for r in news_results]:
                        news_results.append(item)

            # Try Method 3: Fallback div parsing
            if len(news_results) == 0:
                fallback_results = _parse_news_from_divs(soup)
                for item in fallback_results:
                    if item['title'] not in [r['title'] for r in news_results]:
                        news_results.append(item)

            # If still no results on first page, stop
            if page == 0 and len(news_results) == 0:
                break

            # Check for the "Next" link (pagination)
            next_link = soup.find("a", id="pnnext")
            if not next_link:
                break

            page += 1

        except Exception as e:
            print(f"Error fetching Google News: {e}")
            break

    # Deduplicate by title
    seen_titles = set()
    unique_results = []
    for item in news_results:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            unique_results.append(item)

    return unique_results
