# Generative IoT Project

An LLM-assisted IoT prototype builder: describe an IoT project in plain language, and it
returns the exact components needed (via RAG over a component catalog), validates that the
system is buildable, then generates a step-by-step pin-by-pin wiring plan with a confidence score.

## How it works

```
Streamlit UI ──▶ FastAPI /query ──▶ LangGraph agent
                                      │ planner   : query → structured requirements JSON
                                      │ retriever : per-category vector search in Qdrant
                                      │ responder : validates component selection (system_valid, confidence)
                                      ▼ wiring    : pin layouts → step-by-step wiring plan (NL) + confidence
```

- **Ingestion**: `DATA/components.json` → 1 component = 1 Document = 1 vector in Qdrant
  (embedded with `sentence-transformers/all-mpnet-base-v2`, 768-d, cosine).
- **Knowledge**: `DATA/pins/<type>.json` holds pin layouts for every component (pins, functions,
  voltage ranges, VCC/GND, I2C/SPI/UART interfaces), keyed by the same ids as `components.json`.
- **Reasoning**: Groq `openai/gpt-oss-120b` using JSON mode
  (`response_format={"type": "json_object"}`) — tool-calling is unreliable on this model/API.
- **Observability**: logfire traces every graph node.

## Architecture

| Path | Purpose |
| --- | --- |
| `app/ingestion/` | Load → chunk (1:1) → embed → store pipeline |
| `app/services/retrieval/` | `EmbeddingService` + `QdrantService` |
| `app/services/pins/` | `PinLayoutLoader` (indexes `DATA/pins` by id/name) |
| `app/agents/` | LangGraph: `planner` → `retriever` → `responder` → `wiring` |
| `app/main.py` | FastAPI app (`/query`, `/graph`, `/`) |
| `ui/frontend.py` | Streamlit UI |
| `DATA/` | `components.json` + `pins/<type>.json` |

## Setup

```bash
git clone git@github.com:77Gaurav/generative-iot-project.git
cd generative-iot-project

uv venv --python 3.12 .venv
uv pip install -r requirements-torch-cpu.txt    # CPU-only torch (no CUDA deps)
uv pip install -r requirements.txt

cp .env.example .env                            # then fill in real API keys
```

Required env vars (see `.env.example`):

- `QDRANT_API_KEY`, `QDRANT_CLUSTER_ENDPOINT` — Qdrant cloud
- `GROQ_API_KEY` — https://console.groq.com/keys
- `LOGFIRE_TOKEN` — optional; observability enabled if present

## Run

```bash
# 1. Seed the vector DB (60 components → 60 vectors in Qdrant)
.venv/bin/python -m app.ingestion.processor

# 2. Start the API (terminal 1)
.venv/bin/python -m uvicorn app.main:app --port 8000

# 3. Start the UI (terminal 2) → http://localhost:8501
.venv/bin/python -m streamlit run ui/frontend.py
```

Or test the API directly:

```bash
curl -s http://localhost:8000/query \
  -X POST -H "Content-Type: application/json" \
  -d '{"q":"We are building a weather monitoring IoT project to measure humidity, temperature and rainfall and display readings on a screen."}'
```

## API response

`POST /query` returns `question`, `answer` (`system_valid`), `components`, `checks`,
`missing_requirements`, `confidence`, `wiring` (summary, steps, warnings, confidence),
`pin_layouts`, `requirements`, `thought_process`, `status`, and `sources`.

## Notes

- `gpt-oss-120b` fails to request schema-adjacent output; the JSON-mode helper
  `app/agents/nodes/_json.py` embeds the JSON schema in the prompt and validates/retries.
- Groq free tier has a low tokens-per-minute limit; repeated fast queries can hit HTTP 429.
- See `PROGRESS.md` for the detailed build log.