import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential


class GovernmentCrawler:
    def __init__(self, source_config: dict):
        self.config = source_config
        self.base_url = source_config["base_url"]
        self.visited = set()
        self.results = {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.text

    def is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)
        allowed_netloc = urlparse(self.base_url).netloc
        if parsed.netloc != allowed_netloc:
            return False
        path = parsed.path
        if not any(path.startswith(p) for p in self.config.get("allowed_path_prefixes", [])):
            return False
        if any(d in path for d in self.config.get("denied_path_keywords", [])):
            return False
        return True

    def start(self, max_pages: int = 100) -> dict:
        seeds = list(self.config["seeds"])
        queue = list(seeds)

        while queue and len(self.results) < max_pages:
            url = queue.pop(0)
            if url in self.visited:
                continue
            self.visited.add(url)

            if url not in seeds and not self.is_valid_url(url):
                continue

            try:
                html = self.fetch(url)
                self.results[url] = {"html": html}

                soup = BeautifulSoup(html, "html.parser")
                for link in soup.find_all("a", href=True):
                    full_url = urljoin(url, link["href"])
                    if full_url not in self.visited and full_url not in queue:
                        queue.append(full_url)

                time.sleep(0.5)
            except Exception as e:
                print(f"Failed {url}: {e}")

        return self.results
