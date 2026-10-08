# High Level Design (HLD)

**Project:** Personalized Learning RAG Assistant for Healthcare Exam Prep
**Status:** Draft v1
**Last updated:** 2026-10-08

---

## 1. Purpose & Scope

Design a retrieval-augmented learning assistant that gives healthcare exam candidates
(primarily nurses and newcomers) answers that are **Grounded** (cited from trusted
material), **Personalized** (fit to the learner's level and pace), and **Pedagogical**
(structured with teaching frameworks like STAR and design-thinking scaffolding).

**In scope (v1):** document + image ingestion, retrieval, personalized and
framework-structured answer generation, upload-and-ask over a UI, evaluation hooks.

**Out of scope (v1):** patient clinical advice/diagnosis, from-scratch 3D organ modeling
(we integrate existing anatomy viewers/images in a later phase).

---

## 2. System Context (C4 — Level 1)

```
            ┌───────────────────────────────────────────────┐
            │                  Learner                       │
            │  (nurse / newcomer preparing for exam)         │
            └───────────────┬───────────────────────────────┘
                            │ asks questions, uploads notes/images
                            ▼
            ┌───────────────────────────────────────────────┐
            │        Personalized Learning RAG System        │
            │  grounded + leveled + framework-structured      │
            └───┬───────────────┬───────────────┬────────────┘
                │               │               │
         ┌──────▼─────┐  ┌──────▼──────┐  ┌─────▼───────┐
         │ LLM /      │  │ Vector DB   │  │ Anatomy     │
         │ Embedding  │  │ (knowledge  │  │ viewer /    │
         │ Provider   │  │  base)      │  │ media (ph2) │
         └────────────┘  └─────────────┘  └─────────────┘
```

**Secondary actor:** Instructor/Admin — uploads curated material, reviews weak-spot analytics.

---

## 3. Architecture Overview (C4 — Level 2, Containers)

```
┌──────────────────────────────────────────────────────────┐
│  UI Layer        Streamlit (v1) → React (later)           │
│                  upload, ask, see cited + leveled answer   │
├──────────────────────────────────────────────────────────┤
│  API Layer       FastAPI — REST endpoints, auth, schemas   │
├──────────────────────────────────────────────────────────┤
│  Orchestration   RAG pipeline (LlamaIndex / LangChain)     │
│                  • Personalization service                 │
│                  • Prompt templates (STAR, design thinking) │
│                  • Answer composer + citation builder       │
├──────────────────────────────────────────────────────────┤
│  Retrieval       Embeddings + Vector DB (Chroma→pgvector)  │
│                  chunking, metadata filter, hybrid, re-rank │
├──────────────────────────────────────────────────────────┤
│  Ingestion       Loaders (PDF, docx, image/OCR) →          │
│                  clean → chunk → embed → index             │
├──────────────────────────────────────────────────────────┤
│  Model Layer     LLM + embedding provider (configurable)   │
├──────────────────────────────────────────────────────────┤
│  Data/Storage    Knowledge base, learner profiles, logs    │
└──────────────────────────────────────────────────────────┘
```

Each layer is independently replaceable through a defined interface (see LLD and
DESIGN_PATTERNS). Provider, vector DB, chunking, and top-k are config-driven.

---

## 4. Core Components

| Component | Responsibility |
|-----------|----------------|
| **UI** | Capture question + uploads, render answer with citations and level badge, collect feedback |
| **API Gateway (FastAPI)** | Request validation, auth, rate limiting, routing to orchestration |
| **Ingestion Service** | Load → clean → chunk → embed → index documents and images (OCR) |
| **Retriever** | Embed query, vector + metadata search, hybrid search, re-rank top-k |
| **Personalization Service** | Maintain learner profile (level, pace, history, preferred example style); choose difficulty + style |
| **Prompt Template Engine** | Compose prompts using STAR / design-thinking / scaffolding templates and the learner profile |
| **Answer Composer** | Call LLM with grounded context, enforce "answer only from context", attach citations |
| **Evaluation Hook** | Log query → chunks → answer → feedback; feed eval pipeline (RAGAS/DeepEval) |
| **Storage** | Vector store (KB), relational store (profiles, logs), object store (uploads) |

---

## 5. Primary Data Flow

**Ask-a-question flow:**
1. Learner submits a question (optionally with an upload) via UI.
2. API validates and forwards to Orchestration.
3. If an upload exists → Ingestion processes it on the fly (chunk + embed).
4. Retriever embeds the query, searches the vector DB, applies metadata filters, re-ranks.
5. Personalization Service loads the learner profile → picks level + example style.
6. Prompt Template Engine builds a grounded, framework-structured, level-appropriate prompt.
7. Answer Composer calls the LLM, enforces grounding, attaches citations.
8. UI renders the answer + sources + level badge; collects thumbs feedback.
9. Evaluation Hook logs the full trace and updates the learner profile signal.

---

## 6. Technology Stack (v1 defaults, all swappable)

| Concern | Choice (v1) | Swap options |
|---------|-------------|--------------|
| Language | Python 3.11+ | — |
| API | FastAPI | Flask, Django REST |
| RAG framework | LlamaIndex (or LangChain) | the other |
| Vector DB | ChromaDB (local) | pgvector, Pinecone, Weaviate |
| LLM / Embeddings | Configurable (OpenAI / Anthropic / Bedrock / Ollama) | any |
| UI | Streamlit | React + Vite |
| Eval | RAGAS / DeepEval | TruLens |
| Packaging | Docker + Compose | — |

---

## 7. Non-Functional Requirements

| Attribute | Target / Approach |
|-----------|-------------------|
| **Grounding** | Answers cite sources; model instructed to say "I don't know" when context is missing |
| **Latency** | p95 < 5s for a typical query (tunable via top-k, model) |
| **Scalability** | Stateless API + UI containers scale horizontally; ingestion runs as a job/worker |
| **Portability** | Container-first, cloud-agnostic; same images local and prod |
| **Security** | Secrets in env/secret manager; PII handling for uploads; no secrets in code |
| **Observability** | Structured logs of query→chunks→answer; latency + token/cost metrics |
| **Safety/Compliance** | Medical-education disclaimer; no patient-specific clinical advice; audit of sources used |
| **Cost** | Token/cost tracking per query; configurable model tiers |

---

## 8. Key Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Hallucination of medical facts | Strict grounding prompt + citations + SME review in eval |
| Poor retrieval quality | Hybrid search + re-ranking + chunking tuning + retrieval metrics |
| Weak personalization signal | Capture feedback + performance; iterate profile model via A/B tests |
| Vendor lock-in | Provider abstraction (Strategy/Factory), config-driven |
| Sensitive data in uploads | PII scrubbing, access controls, retention policy |

---

## 9. Roadmap Phases

- **Phase 1 (v1):** RAG core + personalization + framework prompts + upload-and-ask + eval hooks.
- **Phase 2:** Anatomy visualization (embed glTF/Three.js viewer or curated images).
- **Phase 3:** Instructor analytics dashboard (weak-spot insights, cohort trends).
- **Phase 4:** Adaptive learning paths and spaced-repetition scheduling.
