# Design Patterns

**Project:** Personalized Learning RAG Assistant for Healthcare Exam Prep
**Status:** Draft v1
**Last updated:** 2026-10-08

This document lists the design patterns used in the implementation, where each applies,
and why. Patterns are grouped into **architectural** and **object-oriented (GoF)**.

---

## 1. Architectural Patterns

### 1.1 Layered (N-tier) Architecture
- **Where:** the whole system — UI → API → Orchestration → Retrieval → Ingestion → Model → Storage.
- **Why:** clear separation of concerns; each layer is testable and replaceable in isolation.

### 1.2 Pipeline / Pipes-and-Filters
- **Where:** ingestion (`load → clean → chunk → embed → index`) and query
  (`embed → retrieve → rerank → personalize → prompt → generate → cite`).
- **Why:** each stage is a small, composable, independently testable filter; stages can be
  reordered or extended (e.g., add a PII-scrub filter) without touching the rest.

### 1.3 Hexagonal / Ports & Adapters
- **Where:** providers (LLM/embeddings), storage (vector/relational/object).
- **Why:** core logic depends on interfaces (ports), not vendors; adapters implement them.
  Lets us swap OpenAI ↔ Ollama or Chroma ↔ pgvector with no change to orchestration.

### 1.4 Retrieval-Augmented Generation (RAG)
- **Where:** the generation path overall.
- **Why:** grounds answers in retrieved context to minimize hallucination — the core
  trust requirement for medical content.

---

## 2. Object-Oriented / GoF Patterns

### 2.1 Strategy
- **Where:** `LLMProvider` / `EmbeddingProvider` implementations; also the
  personalization "answer strategy" (level/style/framework selection).
- **Why:** interchangeable algorithms chosen at runtime from config; add a provider or a
  teaching strategy without modifying callers. Open/Closed Principle in action.

### 2.2 Factory (Factory Method / Simple Factory)
- **Where:** `provider_factory(LLM_PROVIDER)`, `vector_store_factory(VECTOR_STORE)`.
- **Why:** centralizes object creation driven by config/env; callers never `new` a concrete class.

### 2.3 Repository
- **Where:** `VectorStore`, `ProfileStore`, `ObjectStore` abstractions.
- **Why:** hides persistence details behind a collection-like interface; swap backends and
  mock easily in tests.

### 2.4 Template Method
- **Where:** `PromptBuilder.build()` — fixed skeleton (grounding rule + context + question)
  with framework-specific steps (STAR / design-thinking / scaffolding) filled in.
- **Why:** enforces the non-negotiable grounding/citation structure while varying the
  pedagogical body.

### 2.5 Adapter
- **Where:** `PersonalizationAdapter`; vendor SDK adapters inside each provider.
- **Why:** translate between our domain model and external shapes (SDK payloads, profile → strategy dict).

### 2.6 Builder
- **Where:** composing the final prompt and the structured API response (answer + citations + metadata).
- **Why:** assemble complex objects step-by-step with readable, validated construction.

### 2.7 Observer (event-driven eval)
- **Where:** `EvaluationHook` subscribes to query/feedback events; logging + metrics subscribers.
- **Why:** decouple cross-cutting concerns (eval, metrics, profile updates) from the request path.

### 2.8 Dependency Injection
- **Where:** FastAPI dependencies wire retriever, provider, stores into routes.
- **Why:** inversion of control; makes components swappable and unit-testable with fakes.

### 2.9 Singleton (scoped)
- **Where:** config/settings object, provider client, vector-store client.
- **Why:** reuse expensive clients/connections across requests (managed via DI container, not globals).

### 2.10 Facade
- **Where:** the Orchestration service exposes a single `answer_question()` entry that hides
  retrieval + personalization + generation + citation steps from the API layer.
- **Why:** simple interface over a complex subsystem.

---

## 3. Pattern → Module Mapping

| Pattern | Module(s) |
|---------|-----------|
| Layered | whole repo structure |
| Pipeline | `ingestion/`, `retrieval/` + `generation/` flow |
| Hexagonal / Ports & Adapters | `providers/`, `storage/` |
| Strategy | `providers/*`, `personalization/adapter.py` |
| Factory | provider & vector-store factories in `providers/`, `storage/` |
| Repository | `storage/vector_store.py`, `storage/profile_store.py` |
| Template Method | `generation/prompt_builder.py`, `prompts/*.md` |
| Adapter | `personalization/adapter.py`, provider SDK adapters |
| Builder | `generation/composer.py`, `api/schemas.py` response build |
| Observer | `evaluation/evaluator.py`, logging/metrics |
| Dependency Injection | `api/*`, `main.py` app factory |
| Singleton (scoped) | `core/config.py`, provider/store clients |
| Facade | orchestration `answer_question()` |

---

## 4. Principles Behind the Choices

- **SOLID** — especially Open/Closed (Strategy/Factory) and Dependency Inversion (Ports & Adapters).
- **Config over code** — behavior switches live in `.env`, not in branches scattered across modules.
- **Testability first** — every external dependency sits behind an interface so it can be faked.
- **Fail safe on grounding** — the one invariant no pattern is allowed to break: answers stay
  grounded and cited, or the system says "I don't know".
