# Low Level Design (LLD)

**Project:** Personalized Learning RAG Assistant for Healthcare Exam Prep
**Status:** Draft v1
**Last updated:** 2026-10-08

This document details modules, interfaces, data schemas, API contracts, sequence flows,
and prompt templates. It is the implementation-level counterpart to `HIGH_LEVEL_DESIGN.md`.

---

## 1. Proposed Repository Layout

```
RAG_PIPELINE/
├── app/
│   ├── api/                 # FastAPI routers, request/response schemas
│   │   ├── routes_query.py
│   │   ├── routes_ingest.py
│   │   └── schemas.py
│   ├── core/                # config, logging, settings
│   │   ├── config.py
│   │   └── logging.py
│   ├── ingestion/           # loaders, cleaners, chunkers, indexer
│   │   ├── loaders.py
│   │   ├── chunker.py
│   │   └── indexer.py
│   ├── retrieval/           # embedding + vector search + rerank
│   │   ├── embedder.py
│   │   ├── retriever.py
│   │   └── reranker.py
│   ├── personalization/     # learner profile + difficulty/style selection
│   │   ├── profile.py
│   │   └── adapter.py
│   ├── prompts/             # versioned prompt templates
│   │   ├── star.md
│   │   ├── design_thinking.md
│   │   └── scaffolding.md
│   ├── generation/          # prompt builder + LLM call + citation builder
│   │   ├── prompt_builder.py
│   │   ├── composer.py
│   │   └── citations.py
│   ├── providers/           # LLM + embedding provider abstraction
│   │   ├── base.py
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── bedrock_provider.py
│   │   └── ollama_provider.py
│   ├── storage/             # vector store + relational + object store adapters
│   │   ├── vector_store.py
│   │   ├── profile_store.py
│   │   └── object_store.py
│   ├── evaluation/          # eval hooks + RAGAS/DeepEval runners
│   │   └── evaluator.py
│   └── main.py              # FastAPI app factory
├── ui/                      # Streamlit app (v1)
│   └── streamlit_app.py
├── tests/
├── docs/
├── docker/
│   ├── Dockerfile.api
│   └── Dockerfile.ui
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

---

## 2. Key Interfaces (contracts)

### 2.1 LLM / Embedding Provider (Strategy)

```python
# app/providers/base.py
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, *, temperature: float = 0.2,
                 max_tokens: int = 1024) -> str: ...

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

### 2.2 Vector Store (Repository)

```python
# app/storage/vector_store.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Chunk:
    id: str
    text: str
    embedding: list[float]
    metadata: dict          # {source, page, topic, difficulty, doc_id, owner}

@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[Chunk]) -> None: ...
    @abstractmethod
    def query(self, embedding: list[float], top_k: int,
              filters: dict | None = None) -> list[RetrievedChunk]: ...
```

### 2.3 Retriever

```python
# app/retrieval/retriever.py
class Retriever:
    def __init__(self, embedder, vector_store, reranker=None): ...
    def retrieve(self, query: str, top_k: int = 8,
                 filters: dict | None = None) -> list[RetrievedChunk]:
        # 1. embed query
        # 2. vector_store.query(...)
        # 3. optional rerank -> top_n
        ...
```

### 2.4 Personalization

```python
# app/personalization/profile.py
from dataclasses import dataclass
from enum import Enum

class Level(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

@dataclass
class LearnerProfile:
    learner_id: str
    level: Level
    pace: float                 # 0..1 (slow..fast)
    preferred_style: str        # "analogy" | "clinical" | "concise"
    topic_scores: dict          # {topic: 0..1}
    history: list               # recent interactions

# app/personalization/adapter.py
class PersonalizationAdapter:
    def select_strategy(self, profile: LearnerProfile, topic: str) -> dict:
        """Return {level, style, framework, verbosity} used by prompt builder."""
        ...
    def update_from_feedback(self, profile: LearnerProfile,
                             interaction: dict) -> LearnerProfile: ...
```

### 2.5 Prompt Builder (Template Method)

```python
# app/generation/prompt_builder.py
class PromptBuilder:
    def build(self, *, question: str, context: list[RetrievedChunk],
              strategy: dict) -> str:
        # loads template by strategy["framework"] (star/design_thinking/scaffolding)
        # injects level, style, verbosity, context + citations placeholders
        ...
```

---

## 3. API Contracts (FastAPI)

### POST `/api/query`
Request:
```json
{
  "learner_id": "u_123",
  "question": "Explain how the heart pumps blood",
  "topic": "cardiovascular",
  "upload_id": "up_987"          // optional, if an upload was attached
}
```
Response:
```json
{
  "answer": "…leveled, framework-structured answer…",
  "level": "beginner",
  "framework": "star",
  "citations": [
    {"source": "nursing_physio.pdf", "page": 42, "chunk_id": "c_55"}
  ],
  "trace_id": "t_abc",
  "latency_ms": 3120
}
```

### POST `/api/ingest`
Multipart upload (PDF/docx/image). Response:
```json
{ "upload_id": "up_987", "doc_id": "d_55", "chunks_indexed": 128, "status": "indexed" }
```

### POST `/api/feedback`
```json
{ "trace_id": "t_abc", "helpful": true, "understood": true, "comment": "clear!" }
```

### GET `/api/health`
```json
{ "status": "ok", "vector_store": "up", "provider": "openai" }
```

---

## 4. Data Schemas (relational)

**learner_profile**
| column | type | notes |
|--------|------|-------|
| learner_id | PK text | |
| level | enum | beginner/intermediate/advanced |
| pace | float | 0..1 |
| preferred_style | text | analogy/clinical/concise |
| topic_scores | jsonb | {topic: score} |
| updated_at | timestamptz | |

**interaction_log**
| column | type | notes |
|--------|------|-------|
| trace_id | PK text | |
| learner_id | FK | |
| question | text | |
| retrieved_chunk_ids | jsonb | for eval + audit |
| answer | text | |
| framework | text | star/design_thinking/scaffolding |
| level | enum | |
| helpful | bool | from feedback |
| latency_ms | int | |
| token_cost | numeric | |
| created_at | timestamptz | |

**document / chunk metadata** (stored with vectors): `doc_id, source, page, topic,
difficulty, owner, created_at`.

---

## 5. Sequence — Ask a Question (with optional upload)

```
Learner → UI → API /query
UI → (if upload) API /ingest → Ingestion: load→clean→chunk→embed→upsert(VectorStore)
API → Retriever.retrieve(query, filters)
        Retriever → Embedder.embed(query)
        Retriever → VectorStore.query(...) → top_k
        Retriever → Reranker.rerank(...) → top_n
API → PersonalizationAdapter.select_strategy(profile, topic)
API → PromptBuilder.build(question, context, strategy)
API → Composer.generate(prompt)  [LLMProvider]
API → CitationBuilder.attach(answer, context)
API → EvaluationHook.log(trace)
API → UI: {answer, level, framework, citations, trace_id}
UI → API /feedback  → PersonalizationAdapter.update_from_feedback(...)
```

---

## 6. Prompt Templates (versioned, in `app/prompts/`)

### 6.1 STAR (`star.md`)
```
You are a medical exam tutor. Answer ONLY from the provided CONTEXT. If the context
is insufficient, say you don't know.

Learner level: {level}. Preferred style: {style}. Keep verbosity: {verbosity}.

Structure the answer using STAR:
- Situation: set the clinical/exam scenario in one or two lines.
- Task: what the learner needs to understand or do.
- Action: the step-by-step explanation, scaled to {level}.
- Result: the key takeaway + a quick self-check question.

CONTEXT:
{context}

QUESTION: {question}

Cite sources inline as [source:page].
```

### 6.2 Design Thinking (`design_thinking.md`)
```
Explain the concept as a design-thinking journey, grounded ONLY in CONTEXT:
- Empathize: why this matters to a {level} learner / patient.
- Define: the core problem/concept in one sentence.
- Ideate: 2–3 ways to think about it (use {style} examples).
- Prototype: a concrete worked example.
- Test: a question to check understanding.
Say "I don't know" if CONTEXT is insufficient. Cite as [source:page].

CONTEXT: {context}
QUESTION: {question}
```

### 6.3 Scaffolding (`scaffolding.md`)
```
Teach by scaffolding from simple to precise, grounded ONLY in CONTEXT.
1. Plain-language analogy ({style}).
2. The accurate explanation at {level}.
3. The exam-ready precise version.
4. One check-for-understanding question.
Say "I don't know" if CONTEXT lacks the answer. Cite as [source:page].

CONTEXT: {context}
QUESTION: {question}
```

**Grounding rule (all templates):** answer only from retrieved context; never invent
medical facts; always surface citations.

---

## 7. Configuration (`.env` driven)

| Key | Example | Purpose |
|-----|---------|---------|
| `LLM_PROVIDER` | `openai` | which Strategy to load |
| `LLM_MODEL` | `gpt-4o-mini` | model id |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | embeddings |
| `VECTOR_STORE` | `chroma` | chroma/pgvector/pinecone |
| `TOP_K` | `8` | retrieval breadth |
| `RERANK_TOP_N` | `4` | post-rerank size |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `120` | chunking |

---

## 8. Error Handling & Edge Cases

- **No relevant context** → return a safe "I don't have this in the material" answer, no hallucination.
- **Upload parse failure** → return actionable error; don't index partial garbage.
- **Provider timeout** → retry with backoff; fall back to a smaller model if configured.
- **PII in upload** → scrub/flag before indexing per retention policy.
- **Unknown learner** → default profile (intermediate, concise) and start learning signal.

---

## 9. Testing Strategy

- **Unit:** chunker boundaries, metadata tagging, prompt builder output, provider mocks.
- **Integration:** ingest → retrieve round-trip on a fixture corpus; API contract tests.
- **Eval (offline):** gold Q&A set scored with RAGAS/DeepEval (faithfulness, relevance).
- **Regression:** snapshot key prompts; alert if grounding instruction is dropped.
