import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings
from backend.rag.retriever import Retriever
from backend.rag.reranker import Reranker
from backend.rag.query_rewriter import rewrite_query
from backend.rag.prompt_builder import build_prompt
from openai import OpenAI
from sentence_transformers import CrossEncoder
from qdrant_client import QdrantClient

client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
llm = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.llm_base_url)
retriever = Retriever(client)
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
reranker = Reranker(cross_encoder)

query = "can i claim dole if i lost my job last month"

print(f"Original: {query}")
rewritten = rewrite_query(query, llm)
print(f"Rewritten: {rewritten}")

docs = retriever.retrieve(rewritten)
print(f"Retrieved {len(docs)} docs for rewritten query")

for i, d in enumerate(docs[:5]):
    title = d.get("document_title", "N/A")
    agency = d.get("agency", "N/A")
    print(f"  [{i+1}] {title} ({agency})")

print()
top = reranker.rerank(query, docs, settings.rerank_top_k)
print(f"After re-rank: {len(top)} docs")
for i, d in enumerate(top):
    title = d.get("document_title", "N/A")
    agency = d.get("agency", "N/A")
    text = d.get("text", "")[:120]
    print(f"  [{i+1}] {title} ({agency}): {text}")

print()
messages = build_prompt(query, top, [])
print("Prompt built, sending to LLM...")
response = llm.chat.completions.create(
    model=settings.llm_model,
    messages=messages,
    temperature=settings.llm_temperature,
    max_tokens=settings.llm_max_tokens,
)
print(f"Answer: {response.choices[0].message.content}")
