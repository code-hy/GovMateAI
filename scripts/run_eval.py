import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder

from backend.core.config import settings
from backend.rag.orchestrator import RAGOrchestrator


def run_eval():
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    llm = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.llm_base_url)
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    orchestrator = RAGOrchestrator(client, llm, reranker, settings)

    eval_path = "datasets/evaluation/gold_standard.jsonl"
    if not os.path.exists(eval_path):
        os.makedirs("datasets/evaluation", exist_ok=True)
        with open(eval_path, "w") as f:
            f.write(
                '{"question": "Can I claim my laptop on tax?", "agency": "ATO", "required_keywords": ["laptop", "deduction", "depreciation"]}\n'
            )
            f.write(
                '{"question": "How do I get JobSeeker?", "agency": "SERVICES_AUSTRALIA", "required_keywords": ["jobseeker", "income", "report"]}\n'
            )
            f.write(
                '{"question": "What is the shortcut method for working from home?", "agency": "ATO", "required_keywords": ["shortcut", "working from home", "67 cents"]}\n'
            )

    results = {"total": 0, "keyword_found": 0, "citation_found": 0}

    with open(eval_path, "r") as f:
        for line in f:
            test = json.loads(line)
            results["total"] += 1
            print(f"Testing: {test['question']}")

            res = orchestrator.process_query(test["question"])
            ctx = " ".join(d["text"] for d in res["source_docs"])

            if re.search(r"【\d+】", res["answer"]):
                results["citation_found"] += 1

            if any(kw.lower() in ctx.lower() for kw in test["required_keywords"]):
                results["keyword_found"] += 1

    total = results["total"] or 1
    print("\n=========================================")
    print("     GovMate AI Evaluation Report")
    print("=========================================")
    print(f"Total test cases:       {results['total']}")
    print(f"Citation coverage:      {results['citation_found']}/{results['total']} ({results['citation_found']/total*100:.0f}%)")
    print(f"Retrieval accuracy:     {results['keyword_found']}/{results['total']} ({results['keyword_found']/total*100:.0f}%)")


if __name__ == "__main__":
    run_eval()
