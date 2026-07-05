import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from backend.ingestion.processors.html_parser import parse_html_to_markdown

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}
session = requests.Session()

urls = [
    "https://www.servicesaustralia.gov.au/jobseeker-payment",
    "https://www.ato.gov.au/individuals-and-families/your-tax-return/how-to-lodge-your-tax-return",
]

for url in urls:
    resp = session.get(url, headers=headers, timeout=30)
    md, title = parse_html_to_markdown(resp.text)
    agency = "ATO" if "ato.gov.au" in url else "SERVICES_AUSTRALIA"
    print(f"{agency}: {url}")
    print(f"  Title: {repr(title)}")
    print(f"  MD length: {len(md)}")
    print(f"  MD starts with: {md[:100]}...")
    print()
