# Quick Start

Copy-paste each block in order. Expected output is shown below each command.

---

## 1. Prerequisites

| Tool | Install Command / Link | Verify |
|------|-----------------------|--------|
| **Docker Desktop** | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) | `docker compose version` |
| **Git** | [git-scm.com](https://git-scm.com/) | `git --version` |
| **uv** (Python) | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` | `uv --version` |

> **Windows users:** Run all commands in **PowerShell** (not CMD). Use Docker Desktop with WSL2 backend.

---

## 2. Clone & Configure

```powershell
git clone https://github.com/code-hy/GovMateAI.git
cd GovMateAI
cp .env.example .env
```

Expected:
```
Cloning into 'GovMateAI'...
remote: Enumerating objects: ...
Receiving objects: 100% ...
```

Now open `.env` in a text editor and paste your DeepSeek API key:

```
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
```

> Get a free key at https://platform.deepseek.com (sign up → API Keys → Create new key).
> Total cost for all examples in this guide: **less than $0.01**.

---

## 3. Start Backend Services (Docker)

```powershell
docker compose -f docker/docker-compose.yml up -d qdrant postgres
```

Expected:
```
[+] Running 2/2
 ✔ Container docker-qdrant-1    Started
 ✔ Container docker-postgres-1  Started
```

Verify both are running:

```powershell
docker compose -f docker/docker-compose.yml ps
```

Expected:
```
NAME                IMAGE               STATUS              PORTS
docker-qdrant-1     qdrant/qdrant       Up                  ...
docker-postgres-1   postgres:15         Up                  ...
```

---

## 4. Install Python Dependencies

```powershell
uv sync
```

Expected:
```
Resolving ...
Downloading ...
Installing ...
 ✓  Installed in X.XXs
```

This creates a virtual environment (`venv/` or `.venv/`) and installs all packages from `pyproject.toml`.

---

## 5. Ingest Government Data

```powershell
uv run python scripts/run_ingestion.py
```

This crawls ATO and Services Australia websites, parses HTML into clean Markdown, splits into chunks, generates embeddings, and stores them in Qdrant.

Expected output (first run, ~10-15 minutes):
```
Loading seeds.yaml...

--- Starting ingestion for ato ---
Crawling: https://www.ato.gov.au/individuals-and-families
  Tax file number: 3 chunks upserted
  How to lodge your tax return: 5 chunks upserted
  ...

--- Starting ingestion for services_australia ---
Crawling: https://www.servicesaustralia.gov.au/centrelink
  Centrelink: 4 chunks upserted
  ...

Ingestion complete!
```

On re-run, already-processed pages are skipped:
```
Skipping https://www.ato.gov.au/... (already processed)
```

> **Troubleshooting:** Some government pages may be temporarily unavailable. The crawler retries 3 times then skips. Re-run the command later to pick up any skipped pages.

---

## 6. Run the Chat App

```powershell
uv run python -m uvicorn backend.main:app --reload --reload-exclude monitoring/
```

Expected:
```
INFO:     Started server process ...
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Open **http://localhost:8000** in your browser. You should see:

```
┌─────────────────────────────────────────────┐
│  ☰ GovMate AI  Australian Government RAG   │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │                                      │   │
│  │   Ask a question about ATO or        │   │
│  │   Services Australia.                │   │
│  │                                      │   │
│  └──────────────────────────────────────┘   │
│  ┌──────────────────────────────────────┐   │
│  │ Ask about ATO, Centrelink, Medicare...│   │
│  └─────────────────────────────────[Send]┘   │
└─────────────────────────────────────────────┘
```

---

## 7. Test with an Example Question

Type in the chat box:

```
Can I claim my laptop on tax?
```

Expected answer (approximately):
```
Based on the context provided, if your laptop cost more than $300, you cannot claim
the full cost in the year you purchased it. Instead, you must claim the decline in
value (depreciation) over its effective life【1】.

You also need to apportion the deduction if you use the laptop for both work and
private purposes【1】. You must keep written evidence, such as receipts【4】.

【1】 Computers, laptops and software (ATO)
【4】 Documents to support and verify your claims (ATO)
```

Try more:
```
How do I get JobSeeker if I lost my job?
```

```
What benefits can I get if my income is less than $100 per week?
```

---

## 8. (Optional) Launch Monitoring Dashboard

Open a **second terminal** in the same directory:

```powershell
uv run python -m streamlit run monitoring/dashboard.py
```

Expected:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
```

Open **http://localhost:8501** to see real-time metrics:

| Metric | What You'll See |
|--------|----------------|
| Total Queries | Number of questions asked |
| Avg Latency | Response time in seconds |
| Total Cost | DeepSeek API cost in $ |
| Avg Relevance | Judge score (0.0–1.0) |
| Charts | Latency, cost, feedback, relevance, tokens |

---

## 9. Run Evaluation

```powershell
uv run python scripts/run_eval.py
```

Expected:
```
Testing: Can I claim my laptop on tax?
Testing: How do I get JobSeeker?
Testing: What is the shortcut method for working from home?

=========================================
     GovMate AI Evaluation Report
=========================================
Total test cases:       3
Citation coverage:      3/3 (100%)
Retrieval accuracy:     3/3 (100%)
```

---

## Complete Checklist

- [ ] Git clone succeeded
- [ ] `.env` contains a valid `DEEPSEEK_API_KEY`
- [ ] Docker containers `qdrant` and `postgres` are running
- [ ] `uv sync` completed without errors
- [ ] Ingestion completed (100+ pages per agency)
- [ ] Chat app accessible at http://localhost:8000
- [ ] A question returns an answer with citations `【1】`
- [ ] (Optional) Dashboard accessible at http://localhost:8501
- [ ] Evaluation script passes all test cases

---

## Troubleshooting

### "uv : command not found" / "uv is not recognized"
Install uv, then restart your terminal:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### "docker compose : command not found"
Use the older syntax: `docker-compose` (with hyphen). Or install Docker Desktop.

### "Cannot connect to Qdrant"
Ensure Docker containers are running:
```powershell
docker compose -f docker/docker-compose.yml ps
```
If stopped, start them: `docker compose -f docker/docker-compose.yml up -d`

### "Failed to save metrics: connection to server at localhost"
PostgreSQL is optional. The app continues working — metrics fall back to JSON files.

### Ingestion is slow
First run downloads ~600-800 pages. Subsequent runs are near-instant (skips cached pages).

### Some URLs return 404 / WAF blocks
ATO and Services Australia block aggressive crawling. The crawler retries 3 times and skips persistently failing URLs — this is expected and does not affect answer quality.
