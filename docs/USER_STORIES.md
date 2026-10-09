# User Stories — Personalized Learning RAG Assistant

**Project:** ClinReady / Healthcare Exam Prep RAG Assistant
**Status:** Draft v2
**Last updated:** 2026-10-09
**Source of truth:** `HIGH_LEVEL_DESIGN.md`, `LOW_LEVEL_DESIGN.md`, `DESIGN_PATTERNS.md`

This backlog turns the design docs into implementable user stories, grouped by epic
and ordered by dependency.

**Each story uses this structure:**
- **Title** — names the problem/outcome, not just the artifact.
- **Story** — role / goal / reason (the "so that" is the value).
- **Problem** — the gap this closes and why it matters now.
- **Subtasks** — the concrete steps to reach the outcome.
- **Validation** — how we prove it is done (the Definition of Done).

Story IDs (US-0.1, …) are stable and map 1:1 to a feature branch and PR.

**Personas**
- **Learner** — a nurse or newcomer preparing for a healthcare exam.
- **Instructor/Admin** — uploads curated material, reviews analytics.
- **Developer** — builds and maintains the platform.

**Decisions baked in (resolving doc drift)**
- Datastore: **MongoDB Atlas** (app data + Atlas Vector Search). ChromaDB/MySQL references in older docs are superseded.
- UI: **Angular** SPA.
- Repo layout follows the LLD module structure (`providers/`, `storage/`, `retrieval/`, `generation/`, `personalization/`, `ingestion/`, `evaluation/`, `api/`).

---

## Epic 0 — Foundation: make the backend run

> Outcome: a FastAPI service that installs cleanly, boots, connects to MongoDB, and exposes working auth. Everything else builds on this.

### US-0.1 — Make backend dependencies installable and reproducible
**Story:** As a developer, I want a pinned dependency manifest so that anyone can install the backend and get the exact same working environment.
**Problem:** The code imports `fastapi`, `motor`, `pydantic-settings`, `python-jose`, and `passlib`, but there is no manifest. A new machine (or CI) cannot install the project, and unpinned versions would drift and break builds silently.
**Subtasks:**
- Create `backend/requirements.txt` listing: fastapi, uvicorn[standard], motor, pydantic, pydantic-settings, python-jose[cryptography], passlib[bcrypt], python-multipart.
- Pin each package to a known-good version.
- (Optional) add a short install note to a README or the file header.
**Validation:**
- Fresh virtualenv + `pip install -r requirements.txt` completes with no errors.
- `python -c "import fastapi, motor, pydantic_settings, jose, passlib"` succeeds.
- Importing `app.core.config` and `app.auth.security` raises no ModuleNotFoundError.

### US-0.2 — Make required configuration discoverable without leaking secrets
**Story:** As a developer, I want a committed `.env.example` so that I know every setting the app needs and can configure it without reading source or committing secrets.
**Problem:** `core/config.py` reads many env keys (mongo, jwt, cors, uploads, llm, vector search). None are documented, and there is no safe template, so onboarding means guessing and risks hardcoding secrets.
**Subtasks:**
- Create `backend/.env.example` with every key from `Settings`, grouped by section.
- Use safe placeholders (no real keys); mark which values must be changed for production.
- Confirm `.gitignore` keeps real `.env` out while allowing `.env.example`.
**Validation:**
- Every attribute in `Settings` has a corresponding key in `.env.example`.
- `git status` shows `.env.example` tracked and a copied `.env` ignored.
- Copying to `.env` and booting the app loads values with no missing-key errors.

### US-0.3 — Make the service boot and manage its MongoDB connection
**Story:** As a developer, I want a FastAPI app factory with startup/shutdown hooks so that the service starts cleanly, opens the Mongo connection once, and closes it on exit.
**Problem:** There is no application entrypoint. The Mongo client, index creation, and CORS are written but never wired to a running app, so nothing actually runs.
**Subtasks:**
- Create `backend/app/main.py` with an app factory.
- Register CORS from `settings.cors_origins_list`.
- Wire lifespan to `connect_to_mongo` (startup) and `close_mongo_connection` (shutdown).
- Ensure index creation in `mongo.py` runs idempotently on startup.
**Validation:**
- `uvicorn app.main:app` boots with no exceptions against a reachable Mongo.
- Startup logs show the connection opened; shutdown closes it cleanly.
- Re-running startup does not error on existing indexes (idempotent).

### US-0.4 — Give operators a health signal
**Story:** As an operator, I want a `GET /api/health` endpoint so that I can verify the service and its dependencies are up before sending traffic.
**Problem:** With no health check, there is no fast, scriptable way to confirm the API and MongoDB are reachable (needed for Docker, load balancers, CI smoke tests).
**Subtasks:**
- Add a health router returning `{status, vector_store, provider}`.
- Ping MongoDB to reflect real dependency state.
- Register the router in the app factory.
**Validation:**
- `GET /api/health` returns 200 and the documented JSON when Mongo is up.
- When Mongo is unreachable, the response reflects a degraded state rather than crashing.

### US-0.5 — Let a learner create an account
**Story:** As a learner, I want to register with a username and password so that I can have a personalized, persistent account.
**Problem:** Auth helpers (hashing, JWT) exist but are unreachable — there is no registration route, so no user can ever exist to log in.
**Subtasks:**
- Add `POST /api/auth/register` accepting `UserRegister`.
- Hash the password with the existing bcrypt helper; store the user document.
- Reject duplicate username/email with 409; return `UserPublic` (never the hash).
**Validation:**
- Registering a new user returns 201/200 with `UserPublic` and no password field.
- Duplicate username or email returns 409.
- The stored document contains a bcrypt hash, not the plaintext password.

### US-0.6 — Let a learner log in and obtain a token
**Story:** As a learner, I want to log in and receive a token so that I can make authenticated requests.
**Problem:** Even once users exist, there is no way to authenticate a session, so protected routes (query, ingest) cannot be reached.
**Subtasks:**
- Add `POST /api/auth/login` validating credentials against the stored hash.
- Issue a JWT via the existing `create_access_token`; return a `Token` (+ `UserPublic`).
- Return 401 on invalid credentials; confirm `get_current_user` accepts the token.
**Validation:**
- Valid credentials return a usable JWT and `UserPublic`.
- Invalid credentials return 401.
- The issued token authorizes a request through `get_current_user`.

---

## Epic 1 — Pluggable LLM & embedding providers

> Outcome: generation and embeddings run through swappable interfaces, so vendors change by config, not code. Patterns: Ports & Adapters + Strategy + Factory.

### US-1.1 — Define vendor-neutral provider contracts
**Story:** As a developer, I want `LLMProvider` and `EmbeddingProvider` interfaces so that core logic never depends on a specific vendor SDK.
**Problem:** Without a contract, provider code leaks into the pipeline and locks us to one vendor, violating the Open/Closed principle the design mandates.
**Subtasks:** Define abstract `generate()` and `embed()` in `providers/base.py` per the LLD.
**Validation:** Pipeline modules import only the interfaces; a fake provider can satisfy them in tests.

### US-1.2 — Provide a working OpenAI provider
**Story:** As a developer, I want an OpenAI-backed provider so that the system can generate and embed out of the box.
**Problem:** Interfaces alone can't produce answers; we need one real implementation to run end to end.
**Subtasks:** Implement both interfaces using `config.llm_model`/`embedding_model`; read the API key from config; fail clearly if missing.
**Validation:** `generate()` returns text for a prompt; `embed()` output length equals `config.embedding_dimensions`; missing key gives a clear error.

### US-1.3 — Select the provider by configuration
**Story:** As a developer, I want a `provider_factory()` so that switching providers is a config change, not a code change.
**Problem:** Callers must not instantiate concrete providers; creation needs to be centralized and config-driven.
**Subtasks:** Build a factory keyed on `config.llm_provider`; register optional anthropic/bedrock/ollama stubs.
**Validation:** The factory returns the right provider for each config value; an unknown value raises a clear configuration error.

---

## Epic 2 — Durable storage behind clean interfaces

> Outcome: chunks/vectors, profiles, and uploads persist via Repository interfaces over MongoDB Atlas.

### US-2.1 — Define the vector-store contract and data shapes
**Story:** As a developer, I want `Chunk`, `RetrievedChunk`, and a `VectorStore` interface so that retrieval depends on an abstraction, not a backend.
**Problem:** Hardcoding Mongo queries into retrieval makes it untestable and unswappable.
**Subtasks:** Define the dataclasses and abstract `upsert()`/`query()` in `storage/vector_store.py`.
**Validation:** A fake vector store satisfies the interface in a unit test.

### US-2.2 — Persist and search vectors in MongoDB Atlas
**Story:** As a developer, I want an Atlas Vector Search implementation so that chunks and embeddings persist and are searchable.
**Problem:** Retrieval needs a real store; Atlas is the committed datastore.
**Subtasks:** Implement `upsert()` (text+embedding+metadata) and `query()` using `$vectorSearch` with `vector_index_name`/`vector_search_candidates` and metadata filters; document the index definition.
**Validation:** Upserting then querying returns the expected chunk with a score; filters narrow results correctly.

### US-2.3 — Persist learner profiles
**Story:** As a developer, I want a profile repository so that learner profiles persist and mock cleanly.
**Problem:** Personalization needs durable profiles with a sane default for new learners.
**Subtasks:** CRUD for `LearnerProfile` on `learner_profiles`; default (intermediate/concise) for unknown learners.
**Validation:** Save/load round-trips; unknown learner yields the default profile.

### US-2.4 — Store raw uploads safely
**Story:** As a developer, I want an object-store adapter so that raw uploads are saved before ingestion.
**Problem:** Ingestion needs the original file persisted and size-limited.
**Subtasks:** Save under `config.upload_dir`; enforce `max_upload_bytes`; return a stable `upload_id`.
**Validation:** Oversized upload is rejected; saved file is retrievable by `upload_id`.

---

## Epic 3 — Ingestion pipeline (upload → indexed)

> Outcome: a learner's PDF/docx/image becomes retrievable chunks. Pattern: Pipes-and-Filters.

### US-3.1 — Load documents and images into normalized text
**Story:** As a learner, I want to upload PDF/docx/image notes so that my own material can ground answers.
**Problem:** Without loaders, uploaded material cannot enter the knowledge base.
**Subtasks:** Loaders for PDF, docx, and image (OCR) returning text + metadata; actionable error on parse failure (no partial indexing).
**Validation:** Each type loads to clean text; a corrupt file returns a clear error and indexes nothing.

### US-3.2 — Clean and chunk with tunable settings
**Story:** As a developer, I want configurable chunking so that retrieval quality is tunable.
**Problem:** Fixed chunking can't be optimized for recall/precision.
**Subtasks:** Config-driven size/overlap; attach metadata (`doc_id, source, page, topic, difficulty, owner, created_at`).
**Validation:** Changing config changes chunk boundaries; every chunk carries full metadata.

### US-3.3 — Embed and index chunks end to end
**Story:** As a developer, I want an indexer so that uploaded docs become retrievable.
**Problem:** Chunks are useless until embedded and upserted.
**Subtasks:** Run load→clean→chunk→embed→upsert; return chunks-indexed count.
**Validation:** A fixture doc runs the full pipeline and is retrievable afterward.

### US-3.4 — Expose ingestion over the API
**Story:** As a learner, I want `POST /api/ingest` so that I can upload and index material.
**Problem:** The pipeline must be reachable and access-controlled.
**Subtasks:** Multipart upload; auth required; owner recorded; response `{upload_id, doc_id, chunks_indexed, status}`.
**Validation:** Authenticated upload indexes and returns the contract; anonymous upload is rejected.

---

## Epic 4 — Retrieval that grounds answers

### US-4.1 — Retrieve the most relevant chunks for a question
**Story:** As a learner, I want my question matched to relevant material so that answers are grounded.
**Problem:** Generation without retrieval hallucinates — the core trust risk for medical content.
**Subtasks:** `Retriever.retrieve()` embeds the query, calls `VectorStore.query()`, applies filters, returns top-k (default `config.retrieval_top_k`).
**Validation:** For a known corpus, the expected source chunk appears in the top-k.

### US-4.2 — Improve ordering with an optional reranker
**Story:** As a developer, I want an optional reranker so that the best chunks surface first.
**Problem:** Raw vector order isn't always the most relevant; reranking lifts quality.
**Subtasks:** Rerank to top-n; pipeline must also work with reranking disabled.
**Validation:** With reranking on, relevance ordering improves on a fixture set; off, the pipeline still works.

---

## Epic 5 — Personalization that adapts to the learner

### US-5.1 — Remember each learner's level and style
**Story:** As a learner, I want the system to remember my level and style so that answers fit me.
**Problem:** One-size answers don't serve a beginner and an advanced learner equally.
**Subtasks:** Profile holds level, pace, preferred_style, topic_scores, history; persisted via the profile store; defaults for new learners.
**Validation:** A returning learner's profile is loaded and influences the next answer.

### US-5.2 — Choose difficulty and style per question
**Story:** As a learner, I want difficulty and style chosen for me so that explanations match my needs.
**Problem:** The prompt builder needs a concrete strategy, honoring explicit overrides.
**Subtasks:** `select_strategy()` returns `{level, style, framework, verbosity}`; explicit request fields override the profile.
**Validation:** Strategy reflects the profile by default and the override when provided.

### US-5.3 — Learn from feedback
**Story:** As a learner, I want my feedback to refine future answers so that the assistant adapts.
**Problem:** Without a feedback loop, personalization is static.
**Subtasks:** `update_from_feedback()` adjusts profile signals; changes persist.
**Validation:** Negative/positive feedback measurably shifts the next strategy selection.

---

## Epic 6 — Grounded, framework-structured generation

> Invariant: answer only from retrieved context, or say "I don't know". Patterns: Template Method + Builder.

### US-6.1 — Author versioned teaching-framework prompts
**Story:** As a learner, I want answers structured by a teaching framework so that they are easier to learn from.
**Problem:** Unstructured answers teach poorly; frameworks (STAR/design-thinking/scaffolding) improve learning.
**Subtasks:** Create `prompts/star.md`, `design_thinking.md`, `scaffolding.md` with the grounding rule and citation format.
**Validation:** Each template contains the grounding instruction and citation placeholder.

### US-6.2 — Build prompts consistently from context + strategy
**Story:** As a developer, I want a prompt builder so that level/style/context inject consistently.
**Problem:** Ad-hoc prompt assembly risks dropping the non-negotiable grounding rule.
**Subtasks:** Load template by `strategy["framework"]`; inject level/style/verbosity/context/citations.
**Validation:** Output always includes the grounding instruction (regression-guarded) and the chosen framework's structure.

### US-6.3 — Generate cited answers and refuse ungrounded ones
**Story:** As a learner, I want answers that cite sources so that I can trust and verify them.
**Problem:** Uncited or fabricated answers are unsafe for medical study.
**Subtasks:** Composer calls the LLM with the grounded prompt; citation builder attaches `{source, page, chunk_id}`; insufficient context returns a safe "I don't know".
**Validation:** Answers include citations tied to retrieved chunks; empty context yields "I don't know" with no invented facts.

---

## Epic 7 — Orchestration & query API

### US-7.1 — Provide one orchestration entry point
**Story:** As a developer, I want an `answer_question()` facade so that the API stays thin.
**Problem:** Spreading retrieve/personalize/generate/cite across routes is unmaintainable.
**Subtasks:** `answer_question()` runs the full flow and returns a `QueryResponse`; flip `stubbed` to False.
**Validation:** One call produces a grounded, cited, leveled answer with a trace id.

### US-7.2 — Let a learner ask a question over the API
**Story:** As a learner, I want `POST /api/query` so that I can ask and get a leveled, cited answer.
**Problem:** The product's core action must be reachable and authenticated.
**Subtasks:** Accept `QueryRequest` (+ optional upload ref); return `QueryResponse` with `trace_id` and latency; require auth.
**Validation:** Authenticated query returns the contract; anonymous is rejected.

### US-7.3 — Let a learner rate an answer
**Story:** As a learner, I want `POST /api/feedback` so that I can rate an answer.
**Problem:** Feedback is required to close the personalization and evaluation loops.
**Subtasks:** Accept `{trace_id, helpful, understood, comment}`; log it; trigger profile update.
**Validation:** Feedback is persisted against the trace and updates the profile.

---

## Epic 8 — Evaluation & observability

### US-8.1 — Log every interaction trace
**Story:** As a developer, I want each query→chunks→answer→feedback trace logged so that we can audit and evaluate.
**Problem:** Without traces, we can't debug quality or prove grounding.
**Subtasks:** Store question, retrieved chunk ids, answer, framework, level, helpful, latency, token cost; keep logging off the request path (Observer).
**Validation:** A completed query produces a full trace record; logging failure never breaks the response.

### US-8.2 — Score retrieval/answer quality offline
**Story:** As a developer, I want a RAGAS/DeepEval runner over a gold set so that we track faithfulness and relevance.
**Problem:** Quality regressions are invisible without measurement.
**Subtasks:** Runner scores a fixture Q&A set; regression check alerts if the grounding instruction is dropped from prompts.
**Validation:** Runner outputs metrics; removing the grounding line fails the check.

---

## Epic 9 — Angular learner UI

### US-9.1 — Authenticate from the UI
**Story:** As a learner, I want login/register screens so that I can access my account.
**Problem:** The API auth is unusable without a front door.
**Subtasks:** Register + login flows call the API, store the token, handle errors.
**Validation:** A user can register, log in, and reach an authenticated view.

### US-9.2 — Ask a question and optionally attach a file
**Story:** As a learner, I want to ask and optionally upload so that I get grounded answers over my material.
**Problem:** The core interaction needs a usable surface.
**Subtasks:** Question box + file upload call `/api/query` and `/api/ingest`.
**Validation:** Asking returns a rendered answer; uploading indexes and is usable in the next question.

### US-9.3 — Render answers with citations and a level badge
**Story:** As a learner, I want the answer with citations and a level badge so that I can trust and gauge it.
**Problem:** Answers without visible sources/level are hard to trust.
**Subtasks:** Render answer, clickable citations, framework/level badge, thumbs feedback wired to `/api/feedback`.
**Validation:** Citations are visible and clickable; feedback posts successfully.

---

## Epic 10 — Packaging & delivery

### US-10.1 — Run the stack in containers
**Story:** As a developer, I want Docker images + compose so that the stack runs the same locally and in prod.
**Problem:** "Works on my machine" drift blocks reliable delivery.
**Subtasks:** Dockerfile(s) for API (and UI); `docker-compose.yml` brings up the stack; env via `.env`.
**Validation:** `docker compose up` serves the API and UI; health check passes.

### US-10.2 — Catch regressions in CI
**Story:** As a developer, I want lint + tests in CI so that regressions are caught early.
**Problem:** Manual checks miss breakage.
**Subtasks:** Pipeline runs unit + integration tests and a linter on each push.
**Validation:** CI fails on a broken test or lint error; passes on a clean change.

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
