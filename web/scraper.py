import re
import json
from typing import Dict, List, Optional
from core.logger import setup_logger

logger = setup_logger("jarvis.web.scraper")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not available. Web scraping disabled.")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("beautifulsoup4 not available. HTML parsing limited.")


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


class WebScraper:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.available = REQUESTS_AVAILABLE and BS4_AVAILABLE
        self._session = None
        if REQUESTS_AVAILABLE:
            self._session = requests.Session()
            self._session.headers.update(HEADERS)

    def _fetch(self, url: str) -> Optional[str]:
        if not REQUESTS_AVAILABLE:
            return None
        try:
            response = self._session.get(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except requests.Timeout:
            logger.warning(f"Request timed out: {url}")
            return None
        except requests.HTTPError as e:
            logger.warning(f"HTTP error {e.response.status_code}: {url}")
            return None
        except Exception as e:
            logger.error(f"Fetch error for {url}: {e}")
            return None

    def scrape_summary(self, url: str) -> Dict:
        html = self._fetch(url)
        if html is None:
            return {"status": "error", "error": f"Failed to fetch {url}"}

        if not BS4_AVAILABLE:
            # Fallback: strip HTML tags
            clean = re.sub(r"<[^>]+>", " ", html)
            clean = re.sub(r"\s+", " ", clean).strip()
            return {
                "status": "success",
                "url": url,
                "message": f"Scraped {url}",
                "text": clean[:3000],
                "headings": [],
                "links": [],
                "tables": []
            }

        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        # Title
        title = soup.title.string.strip() if soup.title else ""

        # Meta description
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            meta_desc = meta.get("content", "")

        # Headings
        headings = []
        for tag in soup.find_all(["h1", "h2", "h3"], limit=20):
            text = tag.get_text(strip=True)
            if text:
                headings.append({"level": tag.name, "text": text})

        # Main content text
        main = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"})
        content_source = main if main else soup.body if soup.body else soup
        paragraphs = content_source.find_all("p", limit=30) if content_source else []
        body_text = " ".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        # Top links
        links = []
        for a in soup.find_all("a", href=True, limit=20):
            href = a["href"]
            text = a.get_text(strip=True)
            if href.startswith("http") and text:
                links.append({"text": text[:80], "url": href})

        return {
            "status": "success",
            "url": url,
            "message": f"Scraped: {title or url}",
            "title": title,
            "description": meta_desc,
            "headings": headings,
            "body_text": body_text[:3000],
            "links": links[:10]
        }

    def scrape_full(self, url: str) -> Dict:
        result = self.scrape_summary(url)
        if result["status"] == "error":
            return result

        html = self._fetch(url)
        if html and BS4_AVAILABLE:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()
            full_text = soup.get_text(separator="\n", strip=True)
            result["full_text"] = full_text[:8000]
            result["tables"] = self._extract_tables_from_soup(soup)

        return result

    def extract_links(self, url: str) -> Dict:
        html = self._fetch(url)
        if html is None:
            return {"status": "error", "error": f"Failed to fetch {url}"}

        links = []
        if BS4_AVAILABLE:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                # Resolve relative URLs
                if href.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                if href.startswith("http") and text:
                    links.append({"text": text[:100], "url": href})
        else:
            for match in re.finditer(r'href=["\']?(https?://[^\s"\'<>]+)', html):
                links.append({"url": match.group(1), "text": ""})

        # Deduplicate
        seen = set()
        unique_links = []
        for link in links:
            if link["url"] not in seen:
                seen.add(link["url"])
                unique_links.append(link)

        return {
            "status": "success",
            "url": url,
            "message": f"Found {len(unique_links)} links",
            "links": unique_links[:50]
        }

    def extract_tables(self, url: str) -> Dict:
        html = self._fetch(url)
        if html is None:
            return {"status": "error", "error": f"Failed to fetch {url}"}

        if not BS4_AVAILABLE:
            return {"status": "error", "error": "beautifulsoup4 required for table extraction"}

        soup = BeautifulSoup(html, "html.parser")
        tables = self._extract_tables_from_soup(soup)
        return {
            "status": "success",
            "url": url,
            "message": f"Found {len(tables)} tables",
            "tables": tables
        }

    def _extract_tables_from_soup(self, soup) -> List[Dict]:
        tables_data = []
        for table in soup.find_all("table", limit=10):
            rows = []
            # Headers
            headers = []
            header_row = table.find("tr")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells and any(c for c in cells):
                    rows.append(cells)

            if rows:
                tables_data.append({
                    "headers": headers,
                    "rows": rows[:30],
                    "row_count": len(rows)
                })
        return tables_data

    def search_web(self, query: str) -> Dict:
        """Use DuckDuckGo HTML search (no API key required)."""
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        html = self._fetch(url)
        if html is None:
            return {"status": "error", "error": "Search request failed"}

        results = []
        if BS4_AVAILABLE:
            soup = BeautifulSoup(html, "html.parser")
            for result in soup.find_all("div", class_="result", limit=10):
                title_el = result.find("a", class_="result__a")
                snippet_el = result.find("a", class_="result__snippet")
                if title_el:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "url": title_el.get("href", ""),
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else ""
                    })
        else:
            for match in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)<', html):
                results.append({"url": match.group(1), "title": match.group(2), "snippet": ""})

        return {
            "status": "success",
            "query": query,
            "message": f"Found {len(results)} results for '{query}'",
            "results": results
        }

    def fetch_json(self, url: str, params: dict = None) -> Dict:
        """Fetch and parse a JSON API endpoint."""
        if not REQUESTS_AVAILABLE:
            return {"status": "error", "error": "requests not available"}
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "data": data, "url": url}
        except Exception as e:
            return {"status": "error", "error": str(e)}
