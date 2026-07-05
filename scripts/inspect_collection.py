import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings
from qdrant_client import QdrantClient
from collections import Counter

client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

# Get unique document titles in the collection
scroll = client.scroll(
    settings.qdrant_collection_name,
    limit=500,
    with_payload=True,
    with_vectors=False,
)

titles = Counter()
agencies = Counter()
jobseeker_found = False

for p in scroll[0]:
    title = p.payload.get("document_title", "N/A")
    agency = p.payload.get("agency", "N/A")
    titles[title] += 1
    agencies[agency] += 1
    if "jobseeker" in str(p.payload).lower():
        jobseeker_found = True
        if not jobseeker_found:
            print(f"Found JobSeeker chunk:")
            print(f"  Title: {title}")
            print(f"  URL: {p.payload.get('document_url')}")
            print(f"  Text preview: {p.payload.get('text', '')[:200]}")
            print()

print(f"\nTotal points: {scroll[1]}")
print(f"\nAgencies:")
for a, c in agencies.most_common():
    print(f"  {a}: {c}")

print(f"\nTop document titles:")
for t, c in titles.most_common(20):
    print(f"  {t}: {c}")

print(f"\nJobSeeker found: {jobseeker_found}")

# Try a direct query
if not jobseeker_found:
    print("\nSearching for 'jobseeker' in payloads...")
    search = client.scroll(
        settings.qdrant_collection_name,
        limit=500,
        with_payload=True,
        with_vectors=False,
    )
    urls = set()
    for p in search[0]:
        url = p.payload.get("document_url", "")
        if url:
            urls.add(url)
    print(f"All document URLs in collection ({len(urls)}):")
    for u in sorted(urls):
        print(f"  {u}")
