# Cloud Deployment Guide

Deploy GovMate AI to the cloud using free tiers of Vercel, Qdrant Cloud, and Neon. This guide is written for someone who has never deployed a Python app to the cloud before.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Set Up Qdrant Cloud (Vector Database)](#step-1-set-up-qdrant-cloud-vector-database)
4. [Step 2: Set Up Neon (PostgreSQL)](#step-2-set-up-neon-postgresql)
5. [Step 3: Prepare Your GitHub Repository](#step-3-prepare-your-github-repository)
6. [Step 4: Deploy to Vercel](#step-4-deploy-to-vercel)
7. [Step 5: Ingest Data into Cloud Qdrant](#step-5-ingest-data-into-cloud-qdrant)
8. [Step 6: Verify the Deployment](#step-6-verify-the-deployment)
9. [Cost Summary](#cost-summary)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
Browser ──HTTPS──▶ Vercel (FastAPI + Serverless) ──▶ Qdrant Cloud (Vector DB)
                                                    ──▶ Neon (PostgreSQL)
                                                    ──▶ DeepSeek API (LLM)
```

**What moves to the cloud:**

| Component | Local (Docker) | Cloud (Vercel) |
|-----------|---------------|----------------|
| **FastAPI app** | `uvicorn` process | Vercel serverless function |
| **Qdrant** | Local Docker container | Qdrant Cloud free tier |
| **PostgreSQL** | Local Docker container | Neon free tier |
| **DeepSeek API** | External API call | Same (no change) |
| **Frontend assets** | Served by FastAPI | Served by Vercel CDN |

**What does NOT deploy to the cloud:**

- **Cross-encoder re-ranker** (`sentence-transformers`) — excluded because PyTorch is ~800MB and exceeds Vercel's 250MB function size limit. The app falls back to using hybrid search results directly (still high quality).
- **Streamlit dashboard** — remains local. Deploy separately to [Streamlit Community Cloud](https://streamlit.io/cloud) if desired.
- **Ingestion script** — run locally to crawl + embed + upload to cloud Qdrant once.

---

## Prerequisites

| Item | How to Get It |
|------|---------------|
| **GitHub account** | [github.com](https://github.com) — free |
| **Vercel account** | [vercel.com](https://vercel.com) — free, sign in with GitHub |
| **Qdrant Cloud account** | [cloud.qdrant.io](https://cloud.qdrant.io) — free tier (1 GB) |
| **Neon account** | [neon.tech](https://neon.tech) — free tier (0.5 GB) |
| **DeepSeek API key** | [platform.deepseek.com](https://platform.deepseek.com) — pay-as-you-go (~$0.05 total) |
| **Python 3.12+ locally** | [python.org](https://python.org) or [uv](https://docs.astral.sh/uv/) |

---

## Step 1: Set Up Qdrant Cloud (Vector Database)

Qdrant Cloud provides a free managed vector database. This replaces the local Docker Qdrant.

### 1.1 Create a Cluster

1. Go to [cloud.qdrant.io](https://cloud.qdrant.io) and sign up
2. Click **"Create cluster"**
3. Choose the **Free Tier** plan (1 GB storage, enough for this project)
4. Select a region close to you (e.g., `us-east-1`)
5. Name it `govmate-ai`
6. Click **"Create"** and wait ~2 minutes for provisioning

### 1.2 Get Connection Details

Once the cluster is ready:

1. Click on your cluster name
2. Go to the **"Access"** tab
3. Under **"REST API"**, copy:
   - **Cluster URL** (looks like `https://xxxx-xxxxx.us-east-1-0.aws.cloud.qdrant.io:6333`)
4. Under **"Authentication"**, copy:
   - **API Key** (a long string like `eyJhbGciOiJIUz...`)

### 1.3 Set Environment Variables

These values will be used in Step 4 when configuring Vercel.

```
QDRANT_HOST = your-cluster-url (without https:// and without :6333)
QDRANT_PORT = 6333
QDRANT_API_KEY = your-api-key
QDRANT_HTTPS = true
```

---

## Step 2: Set Up Neon (PostgreSQL)

Neon provides a free serverless PostgreSQL database. This replaces the local Docker Postgres.

### 2.1 Create a Project

1. Go to [neon.tech](https://neon.tech) and sign up
2. Click **"Create a project"**
3. Name it `govmate-ai`
4. Select a region (preferably same as Qdrant Cloud)
5. Click **"Create project"**

### 2.2 Get Connection String

1. On the project dashboard, find the **"Connection Details"** section
2. Copy the **"Connection string"** (PSQL) — it looks like:
   ```
   postgresql://username:password@ep-xxxxx.us-east-1.aws.neon.tech/govmate-ai?sslmode=require
   ```

This is your `DATABASE_URL` for Vercel.

---

## Step 3: Prepare Your GitHub Repository

The repository already includes the files needed for Vercel deployment:

| File | Purpose |
|------|---------|
| `api/asgi.py` | Vercel entry point — imports the FastAPI app |
| `vercel.json` | Build and routing configuration |
| `requirements.txt` | Python dependencies for Vercel (lighter than local) |
| `runtime.txt` | Specifies Python 3.12 |

### Key Differences from Local Setup

| Aspect | Local | Vercel |
|--------|-------|--------|
| **Re-ranker** | Cross-Encoder (`sentence-transformers`) | Disabled (too heavy for serverless) |
| **Static files** | Served by FastAPI `/static` mount | Served by Vercel CDN |
| **Background tasks** | FastAPI `BackgroundTasks` | May not complete — metrics saved synchronously |
| **Ingestion** | Run locally | Run locally once, upload to cloud Qdrant |

Make sure your repository is pushed to GitHub:

```bash
git add .
git commit -m "Add Vercel deployment config"
git push
```

---

## Step 4: Deploy to Vercel

You can deploy either through the Vercel web dashboard or the CLI. The web dashboard is simpler for first-time users.

### Option A: Deploy via Vercel Dashboard (Recommended)

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click **"Add New..."** → **"Project"**
3. Find and select your `govmateai` GitHub repository
4. In the **"Configure Project"** screen:

   **Framework Preset:** Leave as **"Other"** (Vercel auto-detects Python)

   **Root Directory:** Leave as `./`

   **Build and Output Settings:** Leave defaults

5. Click **"Environment Variables"** and add:

   | Name | Value |
   |------|-------|
   | `DEEPSEEK_API_KEY` | `sk-your-deepseek-key-here` |
   | `LLM_MODEL` | `deepseek-chat` |
   | `LLM_BASE_URL` | `https://api.deepseek.com` |
   | `QDRANT_HOST` | Your Qdrant Cloud cluster URL (without `https://` or `:6333`) |
   | `QDRANT_PORT` | `6333` |
   | `QDRANT_API_KEY` | Your Qdrant Cloud API key |
   | `QDRANT_HTTPS` | `true` |
   | `QDRANT_COLLECTION_NAME` | `government_documents` |
   | `DATABASE_URL` | Your Neon connection string |
   | `FASTEMBED_CACHE_PATH` | `/tmp/fastembed` |

6. Click **"Deploy"**

7. Wait ~3-5 minutes for the build. You'll see:
   ```
   ✓ Production: https://govmateai-xxxxx.vercel.app [ready]
   ```

### Option B: Deploy via Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy from project root
vercel --prod
```

When prompted:
- **Set up and deploy:** `Y`
- **Which scope:** your account
- **Link to existing project:** `N`
- **Project name:** `govmateai`
- **Directory:** `./`
- **Override settings:** `N`

Vercel will detect `requirements.txt` and `runtime.txt` automatically. Then set environment variables:

```bash
vercel env add DEEPSEEK_API_KEY
vercel env add QDRANT_HOST
vercel env add QDRANT_PORT
vercel env add QDRANT_API_KEY
vercel env add QDRANT_HTTPS
vercel env add DATABASE_URL
vercel env add FASTEMBED_CACHE_PATH /tmp/fastembed
```

Then deploy:

```bash
vercel --prod
```

### 4.1 Verify the Deployment

1. Vercel gives you a URL like `https://govmateai-xxxxx.vercel.app`
2. Open it in your browser
3. You should see the chat interface
4. **It will error when you ask a question** — this is expected. Data hasn't been ingested yet (Step 5).

> **Troubleshooting:** If you see a 500 error or blank page, check the Vercel deployment logs:
> - Go to your project on [vercel.com](https://vercel.com)
> - Click **"Deployments"** → latest deployment
> - Click **"Functions"** → **"api/asgi.py"**
> - Look for error messages

---

## Step 5: Ingest Data into Cloud Qdrant

The ingestion must be run from your local machine, configured to upload to Qdrant Cloud instead of localhost.

### 5.1 Configure Local Environment

Create a `.env.cloud` file in your project root:

```
DEEPSEEK_API_KEY=sk-your-deepseek-key-here
LLM_MODEL=deepseek-chat
QDRANT_HOST=your-cluster-url (without https:// or :6333)
QDRANT_PORT=6333
QDRANT_API_KEY=your-qdrant-cloud-api-key
QDRANT_HTTPS=true
DATABASE_URL=postgresql://username:password@ep-xxxxx.us-east-1.aws.neon.tech/govmate-ai?sslmode=require
```

### 5.2 Run Ingestion

```bash
# Load cloud environment variables
$env:QDRANT_HOST="your-cluster-url"
$env:QDRANT_PORT="6333"
$env:QDRANT_API_KEY="your-api-key"
$env:QDRANT_HTTPS="true"
$env:DEEPSEEK_API_KEY="sk-your-deepseek-key-here"

# Run ingestion (this uploads to cloud Qdrant)
uv run python scripts/run_ingestion.py
```

Expected output:
```
Loading seeds.yaml...

--- Starting ingestion for ato ---
Crawling: https://www.ato.gov.au/individuals-and-families
  Tax file number: 3 chunks upserted
  ...

--- Starting ingestion for services_australia ---
Crawling: https://www.servicesaustralia.gov.au/centrelink
  Centrelink: 4 chunks upserted
  ...

Ingestion complete!
```

This crawls the government websites, generates embeddings, and uploads to Qdrant Cloud. Takes ~10-15 minutes.

> **Why run locally?** The ingestion uses FastEmbed (CPU-based embedding) and crawls websites. Vercel serverless functions have a 10-second timeout, which is too short for crawling hundreds of pages. Running ingestion once locally is the standard approach — the uploaded vectors in Qdrant Cloud persist forever.

### 5.3 Verify Data in Qdrant Cloud

1. Go to [cloud.qdrant.io](https://cloud.qdrant.io)
2. Click your cluster → **"Collections"** tab
3. You should see the `government_documents` collection with points (documents)
4. Click on the collection to see point count (should be several thousand)

---

## Step 6: Verify the Deployment

### 6.1 Ask a Question

Open your Vercel deployment URL and ask:

```
Can I claim my laptop on tax?
```

Expected response:
```
Based on the context provided, if your laptop cost more than $300, you cannot claim
the full cost in the year you purchased it. Instead, you must claim the decline in
value (depreciation) over its effective life【1】.

You also need to apportion the deduction if you use the laptop for both work and
private purposes【1】. You must keep written evidence, such as receipts【4】.

【1】 Computers, laptops and software (ATO)
【4】 Documents to support and verify your claims (ATO)
```

### 6.2 Check the Health Endpoint

```
https://govmateai-xxxxx.vercel.app/api/v1/health
```

Expected:
```json
{"status": "ok", "qdrant_connected": true}
```

### 6.3 Check Suggestions (Optional)

```
https://govmateai-xxxxx.vercel.app/api/v1/suggestions
```

Expected: a list of 5 suggestion question objects.

---

## Cost Summary

All services are on free tiers suitable for demo/personal use:

| Service | Free Tier Limits | Estimated Monthly Cost |
|---------|-----------------|----------------------|
| **Vercel** | 100 GB-hours serverless, 100 GB bandwidth | $0 |
| **Qdrant Cloud** | 1 GB storage, 1 cluster | $0 |
| **Neon** | 0.5 GB storage, 100 hours compute/month | $0 |
| **DeepSeek API** | Pay-as-you-go (¢14/1M prompt tokens) | ~$0.05 one-time |

**Total: $0/month** for demo usage.

> **When would you need to upgrade?**
> - **Vercel Pro** ($20/mo) — if you exceed 100 GB-hours or need 60s function timeout
> - **Qdrant Cloud** — if you exceed 1 GB of vectors
> - **Neon** — if you exceed 0.5 GB storage

---

## Updating the Deployment

After pushing changes to GitHub, Vercel automatically redeploys:

```bash
git add .
git commit -m "Fix something"
git push
```

Vercel detects the push, rebuilds, and deploys. No manual steps needed.

To force a redeploy without code changes:

```bash
vercel --prod
```

Or from the Vercel dashboard: **Deployments** → three dots → **"Redeploy"**

---

## Limitations of the Vercel Deployment

| Limitation | Details | Workaround |
|-----------|---------|------------|
| **No re-ranker** | Cross-encoder skipped (torch too large) | Hybrid search alone is still effective |
| **No background tasks** | Vercel may terminate functions before judge/metrics finish | Metrics save synchronously before response |
| **10s timeout** | Hobby plan limits function execution to 10s | LLM calls take 3-6s, well within limit |
| **Cold starts** | First request after inactivity is slow (~15s) | Embedding models download to cache on first call |
| **Ingestion not cloud-native** | Must run locally once | One-time setup, then data persists in Qdrant Cloud |
| **No Streamlit dashboard** | Cannot run on Vercel | Deploy to [Streamlit Community Cloud](https://streamlit.io/cloud) separately |

---

## Troubleshooting

### "Application error" / 500 on Vercel

Check function logs in Vercel dashboard: **Deployments** → latest → **Functions** → **api/asgi.py**.

Common causes:
- Missing environment variables (check all are set)
- Qdrant Cloud not accessible (check host/port/api_key)
- FastEmbed model download failed (check `FASTEMBED_CACHE_PATH=/tmp/fastembed`)

### "Cannot connect to Qdrant"

```json
{"status": "error", "qdrant_connected": false}
```

Verify:
- Qdrant Cloud cluster is running (check dashboard)
- `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY`, `QDRANT_HTTPS=true` are all set in Vercel env vars
- `QDRANT_HOST` does NOT include `https://` or `:6333`

### Ingestion uploads to wrong Qdrant

Make sure your terminal's environment variables point to Qdrant Cloud, not localhost:

```powershell
$env:QDRANT_HOST="your-cluster-url"
$env:QDRANT_API_KEY="your-api-key"
$env:QDRANT_HTTPS="true"
```

Verify:
```powershell
echo $env:QDRANT_HOST
```

### "Streamlit not available"

Streamlit is not included in the Vercel requirements. To run the dashboard locally alongside the cloud app:

```bash
uv run python -m streamlit run monitoring/dashboard.py
```

The dashboard reads from `datasets/llm_calls.json`. Since the cloud app doesn't write to this file, the dashboard will show limited data for cloud conversations.

### Deployment takes too long

First deployment downloads and caches FastEmbed models (~30MB). Subsequent deployments are faster (cached).

### "Module not found: sentence_transformers"

This is expected on Vercel — it's excluded from `requirements.txt`. The app runs without the re-ranker. Check that the `try/except` in `backend/main.py` handles this gracefully.

---

## Deploying the Streamlit Dashboard (Optional)

Streamlit Community Cloud is a separate free service for hosting Streamlit apps.

1. Push `monitoring/dashboard.py` to GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Click **"New app"** → select your repo
4. Set the main file path to `monitoring/dashboard.py`
5. Add environment variables: `DATABASE_URL` (your Neon URL)
6. Deploy

Note: The dashboard reads from PostgreSQL when available, and falls back to local JSON files. On Streamlit Cloud, it will use Neon if `DATABASE_URL` is configured.
