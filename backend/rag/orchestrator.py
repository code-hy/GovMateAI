import json

from openai import OpenAI
from qdrant_client import QdrantClient

from backend.core.config import settings
from backend.rag.citation_formatter import format_citations
from backend.rag.prompt_builder import build_prompt
from backend.rag.query_rewriter import rewrite_query
from backend.rag.reranker import Reranker
from backend.rag.retriever import Retriever


class RAGOrchestrator:
    def __init__(
        self,
        qdrant_client: QdrantClient,
        openai_client: OpenAI,
        reranker,
        config: settings,
    ):
        self.config = config
        self.llm = openai_client
        self.retriever = Retriever(qdrant_client)
        self.reranker = Reranker(reranker)
        self.sessions: dict[str, list] = {}

    def process_query(
        self, question: str, session_id: str | None = None
    ) -> dict:
        history = self.sessions.get(session_id, [])[
            -(self.config.max_history_turns * 2) :
        ]

        rewritten = rewrite_query(question, self.llm)
        retrieved_docs = self.retriever.retrieve(rewritten)
        top_k = self.config.rerank_top_k if self.reranker.model else 10
        top_docs = self.reranker.rerank(
            question, retrieved_docs, top_k
        )
        messages = build_prompt(question, top_docs, history)

        response = self.llm.chat.completions.create(
            model=self.config.llm_model,
            messages=messages,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
            stream=False,
        )
        answer = response.choices[0].message.content
        sources = format_citations(answer, top_docs)

        if session_id:
            if session_id not in self.sessions:
                self.sessions[session_id] = []
            self.sessions[session_id].append(
                {"role": "user", "content": question}
            )
            self.sessions[session_id].append(
                {"role": "assistant", "content": answer}
            )

        return {"answer": answer, "sources": sources, "source_docs": top_docs}

    def process_query_stream(
        self, question: str, session_id: str | None = None
    ):
        history = self.sessions.get(session_id, [])[
            -(self.config.max_history_turns * 2) :
        ]
        rewritten = rewrite_query(question, self.llm)
        retrieved_docs = self.retriever.retrieve(rewritten)
        top_k = self.config.rerank_top_k if self.reranker.model else 10
        top_docs = self.reranker.rerank(
            question, retrieved_docs, top_k
        )
        messages = build_prompt(question, top_docs, history)

        full_answer = ""
        stream = self.llm.chat.completions.create(
            model=self.config.llm_model,
            messages=messages,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_answer += content
                yield content

        sources = format_citations(full_answer, top_docs)
        yield f"__SOURCES__{json.dumps(sources)}"
