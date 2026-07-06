import hashlib
import json
import os
from pathlib import Path

import yaml
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    SparseIndexParams,
    SparseVectorParams,
    VectorParams,
)

from backend.core.config import settings
from backend.ingestion.chunkers.markdown_chunker import chunk_markdown
from backend.ingestion.crawlers.base import GovernmentCrawler
from backend.ingestion.embedders.local_embedder import get_embeddings
from backend.ingestion.processors.html_parser import parse_html_to_markdown


def _upload_page(
    client: QdrantClient,
    url: str,
    title: str,
    agency: str,
    markdown_content: str,
):
    chunks = chunk_markdown(markdown_content, {"url": url, "title": title, "agency": agency})
    texts = [c["text"] for c in chunks]
    dense_vectors, sparse_vectors = get_embeddings(texts)

    try:
        old_ids = client.scroll(
            settings.qdrant_collection_name,
            scroll_filter={"must": [{"key": "document_url", "match": {"value": url}}]},
            limit=100,
        )[0]
        if old_ids:
            client.delete(settings.qdrant_collection_name, [p.id for p in old_ids])
    except Exception:
        pass

    points = []
    for i, chunk in enumerate(chunks):
        point_id = hashlib.md5(f"{url}_{i}".encode()).hexdigest()
        points.append(
            PointStruct(
                id=point_id,
                vector={"dense": dense_vectors[i], "sparse": sparse_vectors[i]},
                payload=chunk,
            )
        )
    client.upsert(settings.qdrant_collection_name, points)
    print(f"  {title}: {len(chunks)} chunks upserted")


def _upload_cached_pages(client: QdrantClient, agency_name: str):
    processed_dir = Path(f"datasets/processed/{agency_name}")
    if not processed_dir.exists():
        return
    for json_path in processed_dir.glob("*.json"):
        metadata = json.loads(json_path.read_text(encoding="utf-8"))
        md_path = json_path.with_suffix(".md")
        if not md_path.exists():
            continue
        title = metadata.get("title", "Untitled")
        url = metadata.get("url", "")
        markdown_content = md_path.read_text(encoding="utf-8")
        _upload_page(client, url, title, agency_name.upper(), markdown_content)


def run_ingestion():
    print("Loading seeds.yaml...")
    with open("datasets/seeds.yaml", "r") as f:
        config = yaml.safe_load(f)

    qdrant_kwargs = {
        "host": settings.qdrant_host,
        "port": settings.qdrant_port,
    }
    if settings.qdrant_api_key:
        qdrant_kwargs["api_key"] = settings.qdrant_api_key
    if settings.qdrant_https or settings.qdrant_api_key:
        qdrant_kwargs["https"] = True
    client = QdrantClient(**qdrant_kwargs)

    if not client.collection_exists(settings.qdrant_collection_name):
        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config={
                "dense": VectorParams(
                    size=settings.dense_vector_size, distance=Distance.COSINE
                )
            },
            sparse_vectors_config={"sparse": SparseVectorParams(index=SparseIndexParams())},
        )
        print(f"Created collection '{settings.qdrant_collection_name}'")

    for idx_field in ("agency", "document_url"):
        try:
            client.create_payload_index(
                settings.qdrant_collection_name, idx_field, PayloadSchemaType.KEYWORD
            )
        except Exception:
            pass

    for source in config["sources"]:
        agency_name = source["name"]
        print(f"\n--- Starting ingestion for {agency_name} ---")
        crawler = GovernmentCrawler(source)
        crawled_data = crawler.start(max_pages=200)

        for url, data in crawled_data.items():
            raw_html = data["html"]
            content_hash = hashlib.sha256(raw_html.encode()).hexdigest()

            processed_dir = Path(f"datasets/processed/{agency_name}")
            md_path = processed_dir / f"{content_hash}.md"

            if md_path.exists():
                print(f"Skipping {url} (already processed)")
                continue

            processed_dir.mkdir(parents=True, exist_ok=True)

            markdown_content, title = parse_html_to_markdown(raw_html)
            if len(markdown_content) < 100:
                continue

            md_path.write_text(markdown_content, encoding="utf-8")
            metadata = {
                "url": url,
                "title": title,
                "agency": agency_name.upper(),
                "hash": content_hash,
            }
            json_path = processed_dir / f"{content_hash}.json"
            json_path.write_text(json.dumps(metadata), encoding="utf-8")

            _upload_page(client, url, title, agency_name.upper(), markdown_content)

        print(f"\nUploading cached pages for {agency_name}...")
        _upload_cached_pages(client, agency_name)

    print("\nIngestion complete!")
