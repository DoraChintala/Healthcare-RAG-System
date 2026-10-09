# User Stories — Personalized Learning RAG Assistant

**Project:** ClinReady / Healthcare Exam Prep RAG Assistant
**Status:** Draft v1
**Last updated:** 2026-10-09
**Source of truth:** `HIGH_LEVEL_DESIGN.md`, `LOW_LEVEL_DESIGN.md`, `DESIGN_PATTERNS.md`

This backlog turns the design docs into implementable user stories, grouped by epic
and ordered by dependency. Each story has a role, a goal, a reason, and acceptance
criteria (AC). Stories are sized to be independently shippable where possible.

**Personas**
- **Learner** — a nurse or newcomer preparing for a healthcare exam.
- **Instructor/Admin** — uploads curated material, reviews analytics.
- **Developer** — builds and maintains the platform.

**Decisions baked in (resolving doc drift)**
- Datastore: **MongoDB Atlas** (app data + Atlas Vector Search). ChromaDB/MySQL references in older docs are superseded.
- UI: **Angular** SPA.
- Repo layout follows the LLD module structure (`providers/`, `storage/`, `retrieval/`, `generation/`, `personalization/`, `ingestion/`, `evaluation/`, `api/`).

---

## Epic 0 — Foundation: a runnable API

> Goal: turn the current scaffold into a FastAPI service that boots, with auth reachable and dependencies declared.

### US-0.1 — Dependency manifest
**As a** developer, **I want** a pinned dependency manifest, **so that** the backend installs reproducibly.
**AC**
- `requirements.txt` (or `pyproject.toml`) lists fastapi, uvicorn, motor, pydantic, pydantic-settings, python-jose, passlib[bcrypt], python-multipart.
- Versions are pinned.
- A fresh virtualenv install succeeds with no missing-import errors.

### US-0.2 — Environment template
**As a** developer, **I want** a `.env.example`, **so that** required configuration is discoverable and secrets stay out of code.
**AC**
- `.env.example` lists every key read by `core/config.py` (mongo, jwt, cors, uploads, llm, vector search) with safe placeholder values.
- No real secrets are committed; `.env` remains gitignored.

### US-0.3 — App factory and lifespan
**As a** developer, **I want** a FastAPI app factory with startup/shutdown hooks, **so that** the Mongo client connects on boot and closes on shutdown.
**AC**
- `app/main.py` creates the app, registers CORS from `cors_origins_list`, and wires lifespan to `connect_to_mongo` / `close_mongo_connection`.
- App boots with `uvicorn app.main:app` against a local/Atlas Mongo without raising.
- Indexes defined in `mongo.py` are created idempotently on startup.

### US-0.4 — Health endpoint
**As an** operator, **I want** `GET /api/health`, **so that** I can verify the service and its dependencies are up.
**AC**
- Returns `{status, vector_store, provider}`.
- Returns 200 when Mongo is reachable; reflects degraded state otherwise.

### US-0.5 — User registration
**As a** learner, **I want** to register with username/password, **so that** I can have a personalized account.
**AC**
- `POST /api/auth/register` accepts `UserRegister`, hashes the password (bcrypt), stores the user, rejects duplicate username/email (409).
- Password never returned; response is `UserPublic`.

### US-0.6 — User login
**As a** learner, **I want** to log in, **so that** I receive a token for authenticated requests.
**AC**
- `POST /api/auth/login` validates credentials and returns a `Token` (JWT + `UserPublic`).
- Invalid credentials return 401.
- Protected routes accept the token via `get_current_user`.

---

## Epic 1 — Provider abstraction (LLM + Embeddings)

> Pattern: Ports & Adapters + Strategy + Factory.

### US-1.1 — Provider interfaces
**As a** developer, **I want** `LLMProvider` and `EmbeddingProvider` interfaces, **so that** vendors are swappable without touching callers.
**AC**
- `providers/base.py` defines the abstract `generate()` and `embed()` contracts from the LLD.
- Core logic imports interfaces, never concrete SDKs.

### US-1.2 — OpenAI provider
**As a** developer, **I want** an OpenAI-backed provider, **so that** the system can generate and embed by default.
**AC**
- Implements both interfaces using `config.llm_model` / `config.embedding_model`.
- Reads the API key from config/env; fails clearly if missing.
- Embedding output dimension matches `config.embedding_dimensions`.

### US-1.3 — Provider factory
**As a** developer, **I want** a `provider_factory()` driven by config, **so that** switching providers is a config change.
**AC**
- Returns the correct provider for `config.llm_provider`.
- Unknown provider raises a clear configuration error.
- (Stretch) stubs for anthropic/bedrock/ollama registered but optional.

---

## Epic 2 — Storage (Repository)

> Pattern: Repository over MongoDB Atlas.

### US-2.1 — Vector store interface + models
**As a** developer, **I want** `Chunk`, `RetrievedChunk`, and a `VectorStore` interface, **so that** retrieval depends on an abstraction.
**AC**
- `storage/vector_store.py` defines the dataclasses and abstract `upsert()` / `query()` from the LLD.

### US-2.2 — Atlas Vector Search implementation
**As a** developer, **I want** a MongoDB Atlas vector store, **so that** chunks and embeddings persist and are searchable.
**AC**
- `upsert()` stores chunk text + embedding + metadata.
- `query()` runs `$vectorSearch` using `vector_index_name` and `vector_search_candidates`, supports metadata filters, returns scored results.
- Documents the required Atlas vector index definition.

### US-2.3 — Profile store
**As a** developer, **I want** a profile repository, **so that** learner profiles persist and mock cleanly in tests.
**AC**
- CRUD for `LearnerProfile` on the `learner_profiles` collection.
- Returns a default profile (intermediate/concise) for unknown learners.

### US-2.4 — Object store for uploads
**As a** developer, **I want** an object-store adapter, **so that** raw uploads are saved before ingestion.
**AC**
- Saves files under `config.upload_dir`, enforces `max_upload_bytes`.
- Returns a stable `upload_id`.

---

## Epic 3 — Ingestion pipeline

> Pattern: Pipes-and-Filters.

### US-3.1 — Document loaders
**As a** learner, **I want** to upload PDF/docx/image notes, **so that** my own material is usable for answers.
**AC**
- Loaders handle PDF, docx, and images (OCR) returning normalized text + metadata.
- Parse failure returns an actionable error; no partial indexing.

### US-3.2 — Cleaner + chunker
**As a** developer, **I want** configurable chunking, **so that** retrieval quality is tunable.
**AC**
- Chunk size/overlap are config-driven.
- Each chunk carries metadata: `doc_id, source, page, topic, difficulty, owner, created_at`.

### US-3.3 — Indexer
**As a** developer, **I want** an indexer that embeds and upserts chunks, **so that** uploaded docs become retrievable.
**AC**
- `load → clean → chunk → embed → upsert` runs end to end.
- Returns count of chunks indexed.

### US-3.4 — Ingest endpoint
**As a** learner, **I want** `POST /api/ingest`, **so that** I can upload and index material.
**AC**
- Multipart upload; response `{upload_id, doc_id, chunks_indexed, status}`.
- Requires authentication; owner recorded on chunks.

---

## Epic 4 — Retrieval

### US-4.1 — Query embedder + retriever
**As a** learner, **I want** my question matched to relevant material, **so that** answers are grounded.
**AC**
- `Retriever.retrieve()` embeds the query, calls `VectorStore.query()`, applies filters, returns top-k.
- `top_k` defaults from `config.retrieval_top_k`.

### US-4.2 — Reranker (optional stage)
**As a** developer, **I want** an optional reranker, **so that** top results are the most relevant.
**AC**
- Reranks retrieved chunks to top-n; pipeline works with reranker disabled.

---

## Epic 5 — Personalization

### US-5.1 — Learner profile model + lifecycle
**As a** learner, **I want** the system to remember my level and style, **so that** answers fit me.
**AC**
- Profile holds level, pace, preferred_style, topic_scores, history.
- Persisted via the profile store; defaults applied for new learners.

### US-5.2 — Strategy selection
**As a** learner, **I want** difficulty and style chosen for me, **so that** explanations match my needs.
**AC**
- `PersonalizationAdapter.select_strategy()` returns `{level, style, framework, verbosity}`.
- Explicit request overrides (e.g., level in `QueryRequest`) take precedence over the profile.

### US-5.3 — Feedback-driven update
**As a** learner, **I want** my feedback to refine future answers, **so that** the assistant adapts.
**AC**
- `update_from_feedback()` adjusts profile signals from interaction + feedback.
- Changes persist and influence the next query.

---

## Epic 6 — Generation (grounded, framework-structured)

> Pattern: Template Method + Builder. Invariant: grounded or "I don't know".

### US-6.1 — Prompt templates
**As a** learner, **I want** answers structured by a teaching framework, **so that** they are easier to learn from.
**AC**
- `prompts/star.md`, `design_thinking.md`, `scaffolding.md` exist with the grounding rule and citation format from the LLD.

### US-6.2 — Prompt builder
**As a** developer, **I want** a prompt builder, **so that** level/style/context are injected consistently.
**AC**
- Loads the template for `strategy["framework"]`, injects level/style/verbosity, context, and citation placeholders.
- The grounding instruction is always present (regression-guarded).

### US-6.3 — Answer composer + citations
**As a** learner, **I want** answers that cite their sources, **so that** I can trust and verify them.
**AC**
- Composer calls the LLM with the grounded prompt.
- Citation builder attaches `{source, page, chunk_id}` from retrieved context.
- When context is insufficient, returns a safe "I don't know" with no fabricated facts.

---

## Epic 7 — Orchestration (Facade) + Query API

### US-7.1 — answer_question() facade
**As a** developer, **I want** a single orchestration entry point, **so that** the API stays thin.
**AC**
- `answer_question()` runs retrieve → personalize → prompt → generate → cite and returns a `QueryResponse`.
- `QueryResponse.stubbed` flips to `False` once real RAG is wired in.

### US-7.2 — Query endpoint
**As a** learner, **I want** `POST /api/query`, **so that** I can ask a question and get a leveled, cited answer.
**AC**
- Accepts `QueryRequest` (+ optional upload reference), returns `QueryResponse` with `trace_id` and latency.
- Requires authentication.

### US-7.3 — Feedback endpoint
**As a** learner, **I want** `POST /api/feedback`, **so that** I can rate an answer.
**AC**
- Accepts `{trace_id, helpful, understood, comment}`, logs it, triggers profile update.

---

## Epic 8 — Evaluation & Observability (Observer)

### US-8.1 — Interaction logging
**As a** developer, **I want** every query→chunks→answer→feedback trace logged, **so that** we can audit and evaluate.
**AC**
- Interaction log stores question, retrieved chunk ids, answer, framework, level, helpful, latency, token cost.
- Logging is decoupled from the request path (event/observer).

### US-8.2 — Offline eval harness
**As a** developer, **I want** a RAGAS/DeepEval runner over a gold Q&A set, **so that** we can track faithfulness and relevance.
**AC**
- Runner scores a fixture set and reports metrics.
- A regression check alerts if the grounding instruction is dropped from prompts.

---

## Epic 9 — UI (Angular SPA)

### US-9.1 — Auth screens
**As a** learner, **I want** login/register screens, **so that** I can access my account.
**AC** Register + login flows call the API, store the token, handle errors.

### US-9.2 — Ask + upload
**As a** learner, **I want** to ask a question and optionally attach a file, **so that** I get grounded answers over my material.
**AC** Question box + file upload call `/api/query` and `/api/ingest`.

### US-9.3 — Answer rendering
**As a** learner, **I want** the answer with citations and a level badge, **so that** I can trust and gauge it.
**AC** Renders answer, clickable citations, framework/level badge, and a thumbs feedback control wired to `/api/feedback`.

---

## Epic 10 — Packaging & Delivery

### US-10.1 — Containerization
**As a** developer, **I want** Docker images + compose, **so that** the stack runs the same locally and in prod.
**AC** `Dockerfile` for the API (and UI), `docker-compose.yml` brings up API + UI; env via `.env`.

### US-10.2 — CI checks
**As a** developer, **I want** lint + tests in CI, **so that** regressions are caught early.
**AC** Pipeline runs unit + integration tests and a linter on each push.

---

## Suggested delivery order

1. **Epic 0** — runnable API (unblocks everything).
2. **Epic 1 + 2** — providers + storage (the ports the pipeline plugs into).
3. **Epic 3 + 4** — ingestion + retrieval (grounding data path).
4. **Epic 5 + 6 + 7** — personalization + generation + orchestration (the product).
5. **Epic 8** — evaluation/observability.
6. **Epic 9 + 10** — UI + packaging.

> Tip: this backlog can be promoted into a Kiro **Spec** (requirements → design → tasks)
> for guided, incremental implementation.
