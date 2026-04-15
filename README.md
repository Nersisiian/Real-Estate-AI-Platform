# 🏠 RealEstate AI Platform

[![CI/CD Pipeline](https://github.com/Nersisiian/Real-Estate-AI-Platform/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Nersisiian/Real-Estate-AI-Platform/actions/workflows/ci-cd.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise‑grade, AI‑powered real estate recommendation platform that combines **Retrieval‑Augmented Generation (RAG)** with a **multi‑agent LLM system** built on **LangGraph**.  
The platform offers conversational property search, mortgage calculation, side‑by‑side comparisons, and personalized recommendations, all while keeping costs under control with Redis caching and token management.

---

## 📐 Architecture Overview
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLIENT (React + Vite) │
└─────────────────────────────────┬───────────────────────────────────────────┘
│ HTTP/SSE
┌─────────────────────────────────▼───────────────────────────────────────────┐
│ NGINX (Reverse Proxy) │
└─────────────────────────────────┬───────────────────────────────────────────┘
│
┌─────────────────────────────────▼───────────────────────────────────────────┐
│ FASTAPI BACKEND │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ API LAYER (/api/v1) │ │
│ │ /chat │ /search │ /recommend │ /health │ /admin │ │
│ └───────────────────────────────┬─────────────────────────────────────┘ │
│ │ │
│ ┌───────────────────────────────▼─────────────────────────────────────┐ │
│ │ APPLICATION SERVICES │ │
│ │ • AgentService • RAGRetrievalService │ │
│ │ • RAGIngestionService • RecommendUseCase │ │
│ └───────────────────────────────┬─────────────────────────────────────┘ │
│ │ │
│ ┌───────────────────────────────▼─────────────────────────────────────┐ │
│ │ INFRASTRUCTURE LAYER │ │
│ │ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ │ │
│ │ │ LangGraph │ │ Vector Store │ │ LLM Clients │ │ │
│ │ │ Multi-Agent │ │ (pgvector) │ │ (OpenAI) │ │ │
│ │ │ Orchestrator │ └────────┬─────────┘ └────────┬─────────┘ │ │
│ │ └────────┬─────────┘ │ │ │ │
│ │ │ │ │ │ │
│ │ ┌────────▼─────────┐ ┌────────▼─────────┐ ┌────────▼─────────┐ │ │
│ │ │ Agent Nodes │ │ PostgreSQL │ │ Redis Cache │ │ │
│ │ │ Planner/Retrieval│ │ + pgvector │ │ │ │ │
│ │ │ Tool/Response │ └──────────────────┘ └──────────────────┘ │ │
│ │ └──────────────────┘ │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘


---

## 🧠 Core Features

### 1. Multi‑Agent System (LangGraph)
The system uses a deterministic state machine orchestrated by **LangGraph** with four specialised agents:

- **Planner Agent** – Decomposes user queries, extracts search parameters and determines required tools.
- **Retrieval Agent** – Performs semantic vector search over property embeddings with dynamic filters.
- **Tool Agent** – Executes function calls: `calculate_mortgage`, `compare_properties`, `get_properties`.
- **Response Agent** – Synthesises context, tool results and conversation history into a natural language answer.

Agent communication is stateful with checkpointing for conversation memory.

### 2. RAG (Retrieval‑Augmented Generation) Pipeline
- **Ingestion**: Properties are chunked with a sentence‑aware splitter (configurable overlap). Each chunk is embedded via OpenAI `text-embedding-3-small` and stored in **pgvector**.
- **Retrieval**: User queries are embedded and matched via cosine similarity. Filters (price, location, rooms) are pushed down to the database.
- **Reranking**: Optional cross‑encoder or LLM‑based reranking improves precision.

### 3. Cost Control & Observability
- **Token Management**: Context truncation, token counting, and max‑token limits.
- **Caching**: Redis‑based caching for LLM responses and embeddings (configurable TTL).
- **Fallback Models**: Automatic failover to cheaper models on rate limits or errors.
- **Structured Logging**: JSON logs with request IDs, latency, and token usage.
- **Request Tracing**: Every request receives a unique `X-Request-ID` header.

### 4. Security
- Input validation and prompt‑injection guardrails.
- CORS and Trusted Host middleware.
- Rate limiting (recommended at reverse‑proxy level).

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key

### 1. Clone & Configure
```bash
git clone https://github.com/Nersisiian/Real-Estate-AI-Platform.git
cd Real-Estate-AI-Platform
cp backend/.env.example backend/.env
# Edit backend/.env and set your OPENAI_API_KEY
```
2. Launch with Docker Compose
```
docker-compose up -d --build

This starts:

PostgreSQL with pgvector

Redis

Backend API (FastAPI)

Frontend (React + Vite)

Nginx reverse proxy

----------------------------------------------------------------------------
```
3. (Optional) Seed Sample Data
```
docker-compose exec backend python scripts/seed.py

----------------------------------------------------------------------------
```
4. Access the Application
```
Frontend: http://localhost

API Docs: http://localhost/api/docs (when DEBUG=true)

Health Check: http://localhost/api/health

health
```
📡 API Endpoints
```
Method	Endpoint	Description
POST	/api/v1/chat	Conversational agent (supports SSE streaming)
POST	/api/v1/search	Semantic property search with filters
GET	/api/v1/properties	Traditional property listing
GET	/api/v1/recommend/{id}/similar	Find similar properties
POST	/api/v1/admin/reindex	Trigger reindexing of all properties
```
Example curl Commands
Chat (non‑streaming)
```
curl -X POST http://localhost/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Find me a 3-bedroom house in Austin under $600k"}],
    "stream": false
  }'

Semantic Search
curl -X POST http://localhost/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "modern home with pool",
    "filters": {"city": "Austin", "max_price": 700000},
    "top_k": 5
  }'
```
Similar Properties
```
curl "http://localhost/api/v1/recommend/{property_id}/similar?limit=3"
```
🧪 Testing & Verification
Run the verification script to ensure all components are healthy:
```
chmod +x backend/scripts/verify.sh
./backend/scripts/verify.sh
```
Run backend tests:
```
cd backend
pytest -v
```
🔧 Configuration
Key environment variables (see backend/.env.example):
```
Variable	Description	Default
OPENAI_API_KEY	OpenAI API key	Required
OPENAI_MODEL	Primary chat model	gpt-4o-mini
ENABLE_CACHE	Enable Redis caching	true
MAX_CONTEXT_TOKENS	Max tokens for LLM context	6000
CHUNK_SIZE	RAG chunk size	1000
TOP_K_RETRIEVAL	Number of chunks to retrieve	5
```
📦 Deployment
The application is fully containerised. For production:
```
Set APP_ENV=production and DEBUG=false.

Use a managed PostgreSQL service with pgvector support (e.g., Supabase, Neon).

Use a managed Redis instance.

Deploy with Kubernetes, AWS ECS, or any Docker‑compatible orchestrator.

CI/CD is configured via GitHub Actions (.github/workflows/ci-cd.yml).
