# ragbase

> Multi-tenant knowledge base API with corrective RAG, LangGraph query pipelines, and streaming.

Chat with your documents — PDFs, Word files, Markdown, plain text — organized into named knowledge bases. Built as a production-ready reference for Applied AI engineering.

---

## Stack

| Layer | Technology |
|---|---|
| Orchestration | LangChain + LangGraph |
| LLM & Embeddings | OpenAI GPT-4o-mini + text-embedding-3-small |
| Vector Store | ChromaDB (persistent, multi-collection) |
| API | FastAPI + Uvicorn (streaming SSE) |
| Frontend | SvelteKit 5 (Svelte runes) |
| Containers | Docker Compose |

---

## Architecture

Three pipelines:

```
INGESTION   Documents → Chunker → Embedder → ChromaDB (per KB collection)

QUERY       User query + history
              └─ Contextualize (rewrite for retrieval)
              └─ Retrieve (top-k similarity from ChromaDB)
              └─ Grade docs (LangGraph: relevant or retry?)
                   ├─ relevant → Generate (LLM + citations)
                   └─ not relevant → Rewrite query → Retrieve again

SERVE       FastAPI → SSE stream → SvelteKit UI
```

The query pipeline runs as a **LangGraph stateful graph** with corrective RAG — if retrieved documents score low on relevance, the graph rewrites the query and retrieves again before generating.

---

## Features

- **Multi-tenant** — each knowledge base is a namespaced Chroma collection
- **Multi-format** — PDF, DOCX, TXT, Markdown
- **Corrective RAG** — LangGraph loop grades retrieved docs before generating
- **Streaming** — answers stream token by token via SSE
- **Citations** — every answer includes source document + page number
- **Conversation memory** — multi-turn chat with history-aware retrieval
- **Persistent storage** — ChromaDB survives restarts

---

## Getting started

### Prerequisites

- Python 3.11+
- Node 18+
- OpenAI API key

### Backend

```bash
cd backend
uv venv --python 3.12

source .venv/bin/activate

uv pip install -r requirements.txt

cp .env.example .env
# add your OPENAI_API_KEY to .env

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker (both services)

```bash
docker compose up --build
```

API docs available at `http://localhost:8000/docs`

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/kb` | Create a knowledge base |
| `GET` | `/kb` | List all knowledge bases |
| `DELETE` | `/kb/{id}` | Delete a knowledge base and its vectors |
| `POST` | `/kb/{id}/ingest` | Upload and ingest a document |
| `POST` | `/kb/{id}/query` | Query with streaming SSE response |

### Example

```bash
# Create a KB
curl -X POST http://localhost:8000/kb \
  -H "Content-Type: application/json" \
  -d '{"name": "company-docs", "description": "Internal runbooks and policies"}'

# Ingest a file
curl -X POST http://localhost:8000/kb/{id}/ingest \
  -F "file=@runbook.pdf"

# Query (streaming)
curl -X POST http://localhost:8000/kb/{id}/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the incident response process?", "chat_history": []}'
```

---

## Project structure

```
ragbase/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── kb.py          # knowledge base CRUD
│   │   │   ├── ingest.py      # file upload + ingestion
│   │   │   └── query.py       # streaming query endpoint
│   │   ├── core/
│   │   │   ├── ingestion.py   # load → chunk → embed → store
│   │   │   ├── graph.py       # LangGraph corrective RAG pipeline
│   │   │   └── vectorstore.py # Chroma factory
│   │   ├── models/schemas.py
│   │   ├── config.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── routes/
│       │   ├── +page.svelte        # KB list
│       │   └── kb/[id]/+page.svelte # chat UI
│       └── lib/components/
│           ├── FileUpload.svelte
│           ├── ChatWindow.svelte
│           └── Citations.svelte
├── docker-compose.yml
└── README.md
```

---

## Learning notes

This project was built as a hands-on Applied AI engineering exercise. Key concepts covered:

- **RAG pipeline** — chunking strategy, embedding models, similarity retrieval
- **LangGraph** — stateful graph execution, conditional edges, corrective loops
- **Vector databases** — Chroma collections, metadata filtering, persistence
- **LangChain** — document loaders, text splitters, retrieval chains
- **Streaming** — SSE with FastAPI async generators consumed by SvelteKit
- **Svelte 5 runes** — `$state`, `$derived`, `$effect` reactivity model

---

## Roadmap

- [ ] Hybrid search (BM25 + semantic)
- [ ] Document management (list, delete per KB)
- [ ] Re-ranking with Cohere or cross-encoder
- [ ] Auth (API key per KB)
- [ ] Pinecone swap-in for Chroma

---

## License

MIT

## DEBUG COMMANDS

```
python -c "from app.config import settings; print(settings)"

python -c "
from app.core.vectorstore import get_vectorstore
store = get_vectorstore('test-kb')
print(store._collection.count(), 'docs in collection')
"

python -c "
from app.core.ingestion import ingest
count = ingest('./sample.pdf', kb_id='test-kb', file_name='sample.pdf')
print(f'Stored {count} chunks')
"

python -c "
from app.core.vectorstore import get_vectorstore
store = get_vectorstore('test-kb')
print(store._collection.count(), 'docs stored')
results = store.similarity_search('tell me anything', k=2)
for r in results:
    print('---')
    print(r.metadata)
    print(r.page_content[:200])
"
```

