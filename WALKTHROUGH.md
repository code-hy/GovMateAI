# GovMate AI Walkthrough

A beginner-friendly guide to understanding how this Retrieval-Augmented Generation (RAG) system works — from crawling government websites to answering your questions with citations.

---

## Table of Contents

1. [What is GovMate AI?](#what-is-govmate-ai)
2. [How It Works (No Jargon)](#how-it-works-no-jargon)
3. [The Problem It Solves](#the-problem-it-solves)
4. [The Data: ATO & Services Australia](#the-data-ato--services-australia)
5. [Pipeline Deep Dive](#pipeline-deep-dive)
6. [Running the Project](#running-the-project)
7. [Usage Walkthrough](#usage-walkthrough)
8. [Monitoring Dashboard](#monitoring-dashboard)
9. [Evaluation & Best Practices](#evaluation--best-practices)
10. [Troubleshooting](#troubleshooting)

---

## What is GovMate AI?

GovMate AI is a question-answering chatbot that knows about Australian Government services — specifically the **Australian Taxation Office (ATO)** and **Services Australia** (which runs Centrelink, Medicare, and other social services).

You can ask it questions in plain English:
- *"Can I claim my laptop on tax?"*
- *"How do I get JobSeeker?"*
- *"What benefits can I get if my income is under $100 a week?"*

And it will answer using real government documents, showing you exactly where it found the information with numbered citations like `【1】`.

### What is RAG?

**RAG** stands for **Retrieval-Augmented Generation**. It is a technique that combines two things:

1. **Retrieval** — searching a database of documents to find relevant information
2. **Generation** — using an AI language model (LLM) to write an answer based on that information

Think of it like giving a student (the LLM) an open-book exam. Instead of relying on what the student remembers (which could be wrong), they must look up the answer in the textbook and cite the page number. This eliminates "hallucinations" — the AI making up fake tax rules.

---

## How It Works (No Jargon)

```
Your question → Search government docs → Find best matches → Re-rank by relevance → 
AI writes answer with citations → You see answer + source links
```

**Step by step:**

1. You type a question in the chat box
2. The system rewrites your question to use official terms (e.g., "dole" → "JobSeeker Payment")
3. It searches a vector database (Qdrant) using hybrid search — both meaning and keywords
4. A re-ranker scores the results and picks the top 5 most relevant document chunks
5. Those chunks are fed to the AI (DeepSeek) as context
6. The AI writes an answer, referencing each chunk with `【X】` citation markers
7. The UI renders the answer with clickable source links

---

## The Problem It Solves

Australian Government websites contain thousands of pages of information about taxes, welfare, healthcare, and pensions. Finding the right answer is hard because:

- **Information is scattered** — ATO rules on one site, Centrelink rules on another
- **Language is dense** — "JobSeeker Payment" not "dole," "taxable supply" not "sales tax"
- **Search engines return PDFs** — not direct answers
- **AI models hallucinate** — ChatGPT might invent tax rules that don't exist

GovMate AI solves this by providing a single interface that searches only official `.gov.au` content and produces strictly grounded answers.

---

## The Data: ATO & Services Australia

The system ingests content from two Australian Government agencies:

### Australian Taxation Office (ATO)
~350–450 pages covering:
- Tax deductions (work-related expenses, home office, self-education)
- Investments (property, crypto, shares, capital gains tax)
- Superannuation
- Tax file numbers
- Business GST
- Payment plans and financial hardship

### Services Australia
~300–400 pages covering:
- Centrelink payments (JobSeeker, Youth Allowance, Age Pension, Parenting Payment)
- Medicare (claims, safety net, online account)
- Health care cards (Low Income, Pensioner Concession)
- Carer payments and allowances
- Family assistance (Family Tax Benefit, Child Care Subsidy)
- Crisis payments and special benefit

The URLs for crawling are configured in `datasets/seeds.yaml`. Each agency has a list of allowed URL prefixes, blocked paths (search, login, contact pages, etc.), and seed URLs to start crawling from.

---

## Pipeline Deep Dive

### Stage 1: Ingestion (Crawling → Chunking → Embedding → Storage)

This is the offline process that builds the knowledge base.

```
Government websites → Crawler downloads HTML → Parser extracts text & title →
Chunker splits into 1000-char chunks → Embedder converts to vectors →
Qdrant stores vectors + payload (title, URL, agency, text)
```

**Crawler** (`backend/ingestion/crawlers/base.py`):
- Starts from seed URLs in `seeds.yaml`
- Follows links within the same domain, respecting `allowed_path_prefixes`
- Uses browser-like headers to avoid blocks
- Has retry logic (3 retries with exponential backoff)
- Skips pages smaller than 100 characters of content

**HTML Parser** (`backend/ingestion/processors/html_parser.py`):
- Uses Trafilatura (a library designed for extracting main content from news/government pages)
- Falls back to BeautifulSoup if Trafilatura fails
- Extracts the page title from `<h1>`, `og:title`, or `<title>` tags
- Converts HTML to clean Markdown

**Chunker** (`backend/ingestion/chunkers/markdown_chunker.py`):
- Uses LangChain's `RecursiveCharacterTextSplitter`
- Splits markdown into 1000-character chunks with 200-character overlap
- The overlap ensures no information is lost at chunk boundaries

**Embedder** (`backend/ingestion/embedders/local_embedder.py`):
- Uses FastEmbed (runs on CPU, no GPU needed, no cost)
- Generates **two types of vectors** for each chunk:
  - **Dense vector** (384 dimensions) — captures *meaning* using `BAAI/bge-small-en-v1.5`
  - **Sparse vector** — captures *keyword importance* using BM25
- This dual representation enables **hybrid search**

**Storage** (Qdrant):
- Qdrant is a vector database running in Docker
- Each point (record) contains:
  - Dense vector and sparse vector
  - Payload: text, title, URL, agency, SHA-256 hash
- Payload index on `agency` field enables filtering
- SHA-256 content hashing makes ingestion **idempotent** — re-running skips already-processed pages

### Stage 2: Retrieval (Hybrid Search)

When you ask a question, the system retrieves relevant chunks from Qdrant.

```
Question → Rewriter → Dense Embedding (meaning) + Sparse Embedding (keywords) →
Qdrant RRF Fusion → 15 candidate chunks
```

**Query Rewriting** (`backend/rag/query_rewriter.py`):
- Before searching, the system asks DeepSeek to reformulate your question using formal government terminology
- Example: *"can i claim the dole"* → *"JobSeeker Payment eligibility"*
- This significantly improves retrieval for casual/slang queries
- If the API call fails, the original query is used as-is

**Hybrid Search with RRF** (`backend/rag/retriever.py`):
- The rewritten query is embedded twice:
  1. Dense vector (semantic meaning) — finds conceptually similar content
  2. Sparse vector (BM25 keyword) — finds documents with matching keywords
- Qdrant performs **Reciprocal Rank Fusion (RRF)**: it runs both searches, ranks results, and merges them
- This gives the best of both worlds:
  - *"Can I claim my laptop?"* → dense search finds "computers, laptops and software" by meaning
  - *"JobSeeker waiting period"* → sparse search finds exact term matches
- Top 15 results are returned
- Optional agency filter (ATO vs Services Australia) can be applied

### Stage 3: Re-ranking

The 15 candidate chunks are re-ranked to find the top 5 most relevant ones.

```
15 chunks → Cross-encoder scores each chunk against question → Top 5 selected
```

**Cross-Encoder** (`backend/rag/reranker.py`):
- Uses a specialized model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Unlike the embedding model (which creates one vector per chunk and compares via cosine similarity), a cross-encoder looks at the question AND the chunk together to compute a relevance score
- This is more accurate but slower — that's why we first narrow to 15 with the fast retriever, then re-rank to 5 with the slow but precise model

### Stage 4: Answer Generation

The top 5 chunks are sent to DeepSeek along with a strict prompt.

**Prompt Template** (`backend/rag/prompt_builder.py`):
```
System: You are GovMate AI. Answer STRICTLY using the <context> provided.
        Cite sources using 【X】 format. If context lacks info, say so.

User:
<context>
[1] Agency: ATO | Title: Computers, laptops and software | URL: ...
Laptop deduction rules...

[2] Agency: ATO | Title: Records you need to keep | URL: ...
Receipt retention rules...
</context>

<question>
Can I claim my laptop on tax?
</question>
```

**LLM Call** (`backend/rag/orchestrator.py`):
- Calls DeepSeek API (`deepseek-chat` model)
- Temperature set low (0.0 default) for deterministic, grounded answers
- Max tokens: 512
- Response streams token-by-token to the UI for real-time display

### Stage 5: Citation Formatting

After the answer is generated, the system parses the `【X】` markers and converts them into clickable source links.

**Citation Formatter** (`backend/rag/citation_formatter.py`):
- Uses regex to find all `【X】` patterns in the answer
- Maps each index to the corresponding source document
- Returns structured JSON with index, title, agency, and URL

### Stage 6: Background Evaluation (LLM-as-a-Judge)

After your question is answered, a background task runs:

**Judge** (`backend/rag/judge.py`):
- DeepSeek is asked: *"Rate the relevance of the answer to the question from 0.0 to 1.0"*
- The score is stored alongside the conversation
- This data appears in the monitoring dashboard as "LLM-as-a-Judge Relevance Score"

---

## Running the Project

### Prerequisites

You need two things installed:

1. **Docker Desktop** — to run Qdrant (vector database) and PostgreSQL (monitoring DB)
   - Download from [docker.com](https://www.docker.com/products/docker-desktop/)
2. **uv** — the Python package manager used by this project
   - Install with: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

### Step 1: Clone and Configure

```bash
git clone <your-repo-url>
cd govmateai
cp .env.example .env
```

Edit `.env` and add your DeepSeek API key:
```
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
```

> **Where do I get a DeepSeek API key?**
> Go to [platform.deepseek.com](https://platform.deepseek.com), create an account, and generate an API key. DeepSeek is very affordable — running all the examples in this walkthrough costs less than $0.01.

### Step 2: Start Docker Services

Open Docker Desktop, then run:

```bash
docker compose -f docker/docker-compose.yml up -d qdrant postgres
```

This starts:
- **Qdrant** on port 6333 — the vector database
- **PostgreSQL** on port 5432 — the monitoring database

### Step 3: Install Dependencies and Ingest Data

```bash
uv sync
```

This installs all Python libraries (FastAPI, Qdrant client, DeepSeek SDK, etc.)

```bash
uv run python scripts/run_ingestion.py
```

This will:
1. Read the seed URLs from `datasets/seeds.yaml`
2. Crawl ATO and Services Australia websites
3. Parse HTML to clean Markdown
4. Split into chunks
5. Generate embeddings (dense + sparse)
6. Upload to Qdrant

The first run takes ~10–15 minutes depending on your internet speed. Re-runs skip already-processed pages.

### Step 4: Run the Chat App

```bash
uv run python -m uvicorn backend.main:app --reload --reload-exclude monitoring/
```

Visit **http://localhost:8000** — you should see the chat interface.

### Step 5: (Optional) Launch Monitoring Dashboard

Open a second terminal:

```bash
uv run python -m streamlit run monitoring/dashboard.py
```

Visit **http://localhost:8501** for real-time metrics.

### Running Without Docker

If you don't have Docker, you can run Qdrant directly:

```bash
# Start Qdrant locally
uv run qdrant --port 6333
```

PostgreSQL is optional — the monitoring dashboard falls back to reading from local JSON files (`datasets/llm_calls.json` and `datasets/sessions.json`).

---

## Usage Walkthrough

### Asking Questions

Open http://localhost:8000 and try these examples:

**Example 1: Tax question**
```
You: Can I claim my laptop on tax?
GovMate: Based on the context, if your laptop cost more than $300, you cannot claim 
the full cost in the year you purchased it. Instead, you must claim the decline in 
value (depreciation) over its effective life【1】.

You also need to apportion the deduction if you use the laptop for both work and 
private purposes【1】. You must keep written evidence, such as receipts【4】.

【1】 Computers, laptops and software (ATO)
【4】 Documents to support and verify your claims (ATO)
```

**Example 2: Welfare question with slang**
```
You: can i claim dole if i lost my job last month
GovMate: Yes, you may be eligible to claim JobSeeker Payment (commonly known as 
"the dole") if you lost your job last month. You can start your claim up to 13 
weeks before your circumstances change, so you can apply now【1】【3】.

You will need to meet eligibility rules, such as being unemployed and looking for 
work, and may need to serve waiting periods【1】【5】.

【1】 When to claim (Services Australia)
【3】 Who can get JobSeeker Payment (Services Australia)
```

**Example 3: Unknown information**
```
You: What is the capital gains tax rate for bitcoin mining in Antarctica?
GovMate: I cannot find specific information regarding this in the current documents.
```

### Features

- **Sidebar** — previous conversations are listed on the left. Click one to reload it.
- **New Chat** — click "New Chat" to start a fresh conversation.
- **Thumbs up/down** — rate each answer to help improve quality.
- **Citation links** — click the numbered source links (`【1】`) to open the original government page.
- **Streaming** — answers appear token-by-token as they are generated, like ChatGPT.

---

## Monitoring Dashboard

The Streamlit dashboard at http://localhost:8501 tracks seven metrics:

| Metric | What It Shows |
|--------|---------------|
| Total Queries | How many questions have been asked |
| Avg Latency | Average response time in seconds |
| Total Cost | Cumulative DeepSeek API cost (in dollars) |
| Avg Relevance | Average LLM-as-a-Judge relevance score |
| Query Latency over Time | Line chart of response times |
| Cumulative Cost | Area chart of API spending |
| User Feedback Distribution | Bar chart of thumbs up vs down |
| LLM-as-a-Judge Relevance Score | Line chart of automatic relevance ratings |
| Token Usage | Bar charts of prompt and completion tokens |
| Recent Conversations | Table of the latest 10 interactions |

Data is stored in PostgreSQL when available, or in `datasets/llm_calls.json` as a fallback.

---

## Evaluation & Best Practices

This project implements several RAG best practices:

| Practice | Implementation |
|----------|---------------|
| **Hybrid Search** | Dense (semantic) + Sparse (BM25) vectors fused via Qdrant RRF |
| **Query Rewriting** | DeepSeek reformulates slang into formal terms |
| **Re-ranking** | Cross-encoder model scores and re-orders results |
| **LLM-as-a-Judge** | Background task scores answer relevance automatically |
| **Citation Grounding** | Every answer includes numbered source references |
| **Idempotent Ingestion** | SHA-256 hashing prevents duplicate processing |
| **Streaming Response** | Tokens appear in real-time via HTMX + Server-Sent Events |

See [EVALUATION.md](./EVALUATION.md) for the course evaluation criteria breakdown.

---

## Project Structure

```
govmateai/
├── backend/
│   ├── api/endpoints/       # FastAPI routes (chat, feedback, sessions)
│   ├── core/                # Config, database connection
│   ├── ingestion/           # Crawling, parsing, chunking, embedding
│   ├── models/              # Pydantic schemas
│   └── rag/                 # Retriever, reranker, prompt builder, etc.
├── datasets/
│   ├── seeds.yaml           # URL configuration
│   ├── raw/                 # Downloaded HTML (gitignored)
│   └── processed/           # Cleaned markdown (gitignored)
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   └── templates/           # Jinja2 + HTMX HTML
├── monitoring/
│   └── dashboard.py         # Streamlit dashboard
├── scripts/
│   ├── run_ingestion.py     # Pipeline entry point
│   └── run_eval.py          # Evaluation script
├── .env.example
├── pyproject.toml
└── README.md
```

---

## Troubleshooting

### "I can't connect to localhost:8000"

Make sure uvicorn is running:
```bash
uv run python -m uvicorn backend.main:app --reload --reload-exclude monitoring/
```

### "Failed to connect to Qdrant"

Make sure Docker is running and Qdrant is up:
```bash
docker compose -f docker/docker-compose.yml ps
```

You should see `qdrant` in the "Up" state.

### "DeepSeek API error"

Check your `.env` file has a valid `DEEPSEEK_API_KEY`. You can test it:
```bash
uv run python -c "from openai import OpenAI; c=OpenAI(api_key='sk-...', base_url='https://api.deepseek.com'); print(c.chat.completions.create(model='deepseek-chat', messages=[{'role':'user','content':'hi'}]).choices[0].message.content)"
```

### "No data in monitoring dashboard"

The dashboard reads from `datasets/llm_calls.json`. Ask some questions in the chat app first. If PostgreSQL is not running, the dashboard automatically falls back to the JSON file.

### "Ingestion fails on some URLs"

Some ATO and Services Australia pages may be temporarily unavailable or blocked by WAF (Web Application Firewall). The crawler has retry logic and will skip pages that consistently fail. Re-run `uv run python scripts/run_ingestion.py` later to pick up any missed pages.

---

## Architecture Diagram

```
┌─────────────┐     ┌──────────┐     ┌───────────┐     ┌────────────┐
│  Browser     │────▶│ FastAPI  │────▶│  Qdrant   │────▶│  Crawler   │
│  (HTMX +     │     │  Server  │     │  (Vector  │     │  + Parser  │
│   Tailwind)  │◀────│(Uvicorn) │◀────│   DB)     │     │  + Chunker │
└─────────────┘     └────┬─────┘     └───────────┘     └────────────┘
                         │                                      │
                         ▼                                      ▼
                  ┌──────────────┐                     ┌────────────────┐
                  │  DeepSeek    │                     │  FastEmbed     │
                  │  API (LLM)   │                     │  (Embeddings)  │
                  └──────────────┘                     └────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  PostgreSQL  │
                  │  (Metrics)   │◀──── Streamlit Dashboard
                  └──────────────┘
```

---

## License

MIT
