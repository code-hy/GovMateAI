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
        client.create_payload_index(
            settings.qdrant_collection_name, "agency", PayloadSchemaType.KEYWORD
        )
        print(f"Created collection '{settings.qdrant_collection_name}'")

    for source in config["sources"]:
        print(f"\n--- Starting ingestion for {source['name']} ---")
        crawler = GovernmentCrawler(source)
        crawled_data = crawler.start(max_pages=200)

        for url, data in crawled_data.items():
            raw_html = data["html"]
            content_hash = hashlib.sha256(raw_html.encode()).hexdigest()

            processed_dir = Path(f"datasets/processed/{source['name']}")
            md_path = processed_dir / f"{content_hash}.md"
            json_path = processed_dir / f"{content_hash}.json"

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
                "agency": source["name"].upper(),
                "hash": content_hash,
            }
            json_path.write_text(json.dumps(metadata), encoding="utf-8")

            chunks = chunk_markdown(markdown_content, metadata)

            texts = [c["text"] for c in chunks]
            dense_vectors, sparse_vectors = get_embeddings(texts)

            old_ids = client.scroll(
                settings.qdrant_collection_name,
                scroll_filter={
                    "must": [{"key": "document_url", "match": {"value": url}}]
                },
                limit=100,
            )[0]
            if old_ids:
                client.delete(
                    settings.qdrant_collection_name,
                    [p.id for p in old_ids],
                )

            points = []
            for i, chunk in enumerate(chunks):
                point_id = hashlib.md5(
                    f"{url}_{i}".encode()
                ).hexdigest()
                points.append(
                    PointStruct(
                        id=point_id,
                        vector={
                            "dense": dense_vectors[i],
                            "sparse": sparse_vectors[i],
                        },
                        payload=chunk,
                    )
                )
            client.upsert(settings.qdrant_collection_name, points)
            print(f"  {title}: {len(chunks)} chunks upserted")

    print("\nIngestion complete!")
