# 🏠 RealEstate AI Platform

An enterprise-grade, AI-powered real estate recommendation platform using a multi-agent LLM system with RAG.

[![CI](https://github.com/yourusername/real-estate-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/real-estate-ai/actions/workflows/ci.yml)

## 📐 Architecture Overview
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLIENT (React) │
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

text

## 🧠 Core Features

### 1. Multi-Agent System (LangGraph)
The system uses a state machine orchestrated by **LangGraph** with four specialized agents:

- **Planner Agent**: Decomposes user queries, extracts search parameters, and determines required tools.
- **Retrieval Agent**: Performs semantic vector search over property embeddings with dynamic filters.
- **Tool Agent**: Executes function calls: `calculate_mortgage`, `compare_properties`, `get_properties`.
- **Response Agent**: Synthesizes context, tool results, and conversation history into a coherent natural language response.

Agent communication is fully stateful with checkpointing support for conversation memory.

### 2. RAG (Retrieval-Augmented Generation) Pipeline
- **Ingestion**: Properties are chunked using a sentence-aware splitter with configurable overlap. Each chunk is embedded via OpenAI `text-embedding-3-small` and stored in pgvector.
- **Retrieval**: User queries are embedded and matched via cosine similarity. Filters (price, location, rooms) are applied at the database level.
- **Reranking**: Optional cross-encoder or LLM-based reranking for improved precision.

### 3. Cost Control & Observability
- **Token Management**: Context truncation, token counting, and max token limits.
- **Caching**: Redis-based caching for LLM responses and embeddings (configurable TTL).
- **Fallback Models**: Automatic fallback to cheaper models on rate limits or errors.
- **Structured Logging**: JSON logs with request IDs, latency, and token usage metrics.
- **Request Tracing**: Every request gets a unique `X-Request-ID` header for end-to-end tracing.

### 4. Security
- Input validation and sanitization.
- Prompt injection guardrails.
- Rate limiting (via reverse proxy).
- CORS and Trusted Host middleware.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key

### 1. Clone & Configure
```bash
git clone https://github.com/yourusername/real-estate-ai.git
cd real-estate-ai
cp backend/.env.example backend/.env
# Edit backend/.env with your OPENAI_API_KEY
2. Launch with Docker Compose
bash
docker-compose up -d
This starts:

PostgreSQL with pgvector

Redis

Backend API (FastAPI)

Frontend (React + Vite)

Nginx reverse proxy

3. Initialize Data (Optional)
bash
docker-compose exec backend python scripts/seed.py
4. Access the Application
Frontend: http://localhost

API Docs: http://localhost/api/docs (if DEBUG=true)

Health Check: http://localhost/api/health

📡 API Endpoints
Method	Endpoint	Description
POST	/api/v1/chat	Conversational agent (supports SSE streaming)
POST	/api/v1/search	Semantic property search with filters
GET	/api/v1/properties	Traditional property listing
GET	/api/v1/recommend/{id}/similar	Find similar properties
POST	/api/v1/admin/reindex	Trigger reindexing of all properties
Example curl Commands
Chat:

bash
curl -X POST http://localhost/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Find me a 3-bedroom house in Austin under 600k"}],"stream":false}'
Search:

bash
curl -X POST http://localhost/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"modern home with pool","filters":{"city":"Austin","max_price":700000},"top_k":5}'
Recommend:

bash
curl "http://localhost/api/v1/recommend/{property_id}/similar?limit=3"
🧪 Testing & Verification
Run the verification script to ensure all components are working:

bash
chmod +x backend/scripts/verify.sh
./backend/scripts/verify.sh
Expected output includes health checks, database connectivity, and a test chat request.

Run backend tests:

bash
cd backend
pytest -v
🔧 Configuration
Key environment variables (see backend/.env.example):

Variable	Description	Default
OPENAI_API_KEY	OpenAI API key	Required
OPENAI_MODEL	Primary chat model	gpt-4o-mini
ENABLE_CACHE	Enable Redis caching	true
MAX_CONTEXT_TOKENS	Max tokens for LLM context	6000
CHUNK_SIZE	RAG chunk size	1000
TOP_K_RETRIEVAL	Number of chunks to retrieve	5
📦 Deployment
The application is fully containerized. For production:

Set APP_ENV=production and DEBUG=false.

Use a managed PostgreSQL service with pgvector support (e.g., Supabase, Neon).

Use a managed Redis instance.

Deploy using Kubernetes, AWS ECS, or similar.

CI/CD is configured via GitHub Actions (see .github/workflows/ci.yml).