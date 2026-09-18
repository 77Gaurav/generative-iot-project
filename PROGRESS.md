# Generative IoT Project — Progress Log

Updated: 2026-09-18

## Objective
IoT Prototype RAG: ingest `DATA/components.json` (1 object = 1 Document = 1 Qdrant vector),
embed with `sentence-transformers/all-mpnet-base-v2` (768-d, cosine), then a query flow
Streamlit UI -> FastAPI `/query` -> LangGraph (planner -> retriever -> responder) that
returns a buildable component list with validation. Environment managed with `uv`.

## Architecture
- **Ingestion**: `app/ingestion/loader/objects.py` (1 component JSON = 1 Document),
  `chunking/splitter.py` (one-to-one, no text splitting), `processor.py` orchestration.
- **Services**: `app/services/retrieval/embedding.py` (all-mpnet-base-v2), `qdrant_service.py`
  (Qdrant cloud, collection `generative-iot-project`).
- **Agent** (`app/agents/`): `state.py` (AgentState), `nodes/planner.py` (query -> requirements
  JSON), `nodes/retriever.py` (per-category vector search, merged/deduped), `nodes/responder.py`
  (validation JSON), `graph.py` (planner -> retriever -> responder, `rag_agent`).
- **API/UI**: `app/main.py` (FastAPI `/query`), `ui/frontend.py` (Streamlit).
- **Observability**: logfire (project `gauravp5405/generative-iot-project`,
  `send_to_logfire="if-token-present"`, token in `.env`).

## Completed
- Ingestion pipeline; verified 60 components -> 60 vectors in Qdrant cloud.
- Logfire project set up; records verified.
- Git repo `git@github.com:77Gaurav/generative-iot-project.git`; initial ingest commit pushed.
- Groq structured output fixed: gpt-oss-120b does NOT reliably call tools on Groq
  (HTTP 400 `tool_use_failed`). Switched planner/responder to JSON mode
  (`response_format={"type": "json_object"}`, "json" keyword must appear in messages),
  schema embedded in prompt, parsed via `app/agents/nodes/_json.py` with one retry.
  Parse tool args with `model_validate` (args arrive as a dict, not a JSON string).
- End-to-end verified: graph run + FastAPI `/query` + Streamlit health all pass
  (sample "weather monitoring" query -> ESP32/Raspberry Pi Pico, DHT22, Rain Sensor,
  SSD1306 OLED, LM7805/MP1584, MicroSD; system_valid True, confidence >0.95).
- Environment switched to `uv`: `.venv` recreated with `uv venv` + `uv pip install`;
  committed `requirements.txt` (112 pinned deps) and `requirements-torch-cpu.txt`
  (`torch==2.14.0+cpu` from PyTorch CPU index — split file because uv blocks mixing indexes).
- Pushed LangGraph flow, Streamlit UI, and requirements to `main` (`0bdd306..b851603`).

## How to Run
```bash
source .venv/bin/activate
uvicorn app.main:app --port 8000        # terminal 1
streamlit run ui/frontend.py           # terminal 2 -> http://localhost:8501
```
Optional: re-seed vectors with `.venv/bin/python -m app.ingestion.processor`.

## Current State / Knowns
- Both services can be left running in background (`setsid nohup ... &`); they die between
  shell sessions unless launched detached, so test with single-call patterns.
- Import of `app.main` takes ~8s (torch/sentence-transformers import cost).
- Requirements rebuild:
  `uv pip install -r requirements-torch-cpu.txt && uv pip install -r requirements.txt`.

## Next Steps (open)
- Handle edge-case queries (ill-specified categories, "not in catalog" requirements) more
  gracefully; stress-test with varied prompts.
- [optional] Warm import speed by lazy-loading heavyweight libs; add chat history/state
  persistence; expose `/graph` png from UI.