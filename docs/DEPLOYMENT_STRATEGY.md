# Deployment Strategy

**Project:** Personalized Learning RAG Assistant for Healthcare Exam Prep
**Status:** Draft v1
**Last updated:** 2026-10-08

Container-first and cloud-agnostic. The guiding principle: **the same container images run
locally and in production** — no "works on my machine" gap.

---

## 1. Environments

| Environment | Purpose | Config source |
|-------------|---------|---------------|
| **Local / Dev** | Build + iterate on a laptop | `.env` + docker-compose |
| **Staging** | Pre-prod validation, eval runs, SME review | secrets manager + staging config |
| **Production** | Live learners | secrets manager + prod config |

Each stage uses its own provider keys, vector-store endpoint, and log sink. No secrets in code.

---

## 2. Local / Dev — Docker Compose

Stand up the whole stack with one command:

```
docker compose up --build
```

Services:
- `api` — FastAPI (port 8000)
- `ui` — Streamlit (port 8501)
- `vectordb` — ChromaDB (persistent volume)
- (optional) `postgres` — learner profiles + interaction logs

Example `docker-compose.yml` shape:
```yaml
services:
  api:
    build: { context: ., dockerfile: docker/Dockerfile.api }
    env_file: .env
    ports: ["8000:8000"]
    depends_on: [vectordb, postgres]
  ui:
    build: { context: ., dockerfile: docker/Dockerfile.ui }
    env_file: .env
    ports: ["8501:8501"]
    depends_on: [api]
  vectordb:
    image: chromadb/chroma:latest
    volumes: ["chroma_data:/chroma"]
  postgres:
    image: postgres:16
    environment: { POSTGRES_PASSWORD: ${PG_PASSWORD} }
    volumes: ["pg_data:/var/lib/postgresql/data"]
volumes: { chroma_data: {}, pg_data: {} }
```

---

## 3. Build & Packaging

- **Two images:** `Dockerfile.api` and `Dockerfile.ui`, both from a slim Python base.
- **Multi-stage builds** to keep images small (deps layer cached separately from app code).
- **Pinned dependencies** via `pyproject.toml` / lock file for reproducibility.
- **Non-root user** in the container; read-only filesystem where possible.
- **Health endpoint** (`/api/health`) wired to container healthchecks.

---

## 4. Staging / Production Topology (cloud-agnostic)

```
            ┌──────────────┐
   HTTPS →  │  Load        │
            │  Balancer    │
            └──────┬───────┘
         ┌─────────┴──────────┐
         ▼                    ▼
   ┌───────────┐        ┌───────────┐
   │  UI pods  │        │  API pods │  (stateless, autoscaled)
   └───────────┘        └─────┬─────┘
                              │
             ┌────────────────┼───────────────┐
             ▼                ▼                ▼
      ┌────────────┐   ┌────────────┐   ┌────────────┐
      │ Vector DB  │   │ Postgres   │   │ Object     │
      │ (managed/  │   │ (profiles, │   │ store      │
      │  pgvector) │   │  logs)     │   │ (uploads)  │
      └────────────┘   └────────────┘   └────────────┘
                              │
                     ┌────────▼─────────┐
                     │ Ingestion worker │  (async job for re-indexing)
                     └──────────────────┘
                              │
                     ┌────────▼─────────┐
                     │ LLM / Embedding  │  (managed API or self-hosted)
                     └──────────────────┘
```

**Compute options (pick per cloud):**
- AWS: ECS/Fargate or EKS
- Azure: Container Apps or AKS
- GCP: Cloud Run or GKE

**Why:** API and UI are stateless → scale horizontally and independently. Ingestion runs as
a separate worker/job so re-indexing never blocks live queries.

---

## 5. Data & Model Layer in Prod

| Concern | Dev | Prod |
|---------|-----|------|
| Vector store | ChromaDB (local volume) | Managed pgvector (Postgres) or Pinecone/Weaviate |
| Profiles/logs | Local Postgres | Managed Postgres (backups, PITR) |
| Uploads | Local volume | Object store (S3/GCS/Azure Blob) + lifecycle policy |
| LLM/embeddings | Any provider | Managed API (OpenAI/Anthropic/Bedrock) or self-hosted (vLLM/Ollama) if data residency requires |

Choose self-hosted models when data-residency/compliance forbids sending content to a vendor.

---

## 6. CI/CD Pipeline (GitHub Actions)

```
push / PR
   │
   ├─ lint (ruff) + format check (black)
   ├─ unit + integration tests (pytest)
   ├─ offline RAG eval (RAGAS/DeepEval) on gold set  ── gate on thresholds
   ├─ build images (api, ui)  → push to registry (tagged by git SHA)
   └─ deploy
        ├─ staging  (auto on main)
        └─ production (manual approval / tag release)
```

- **Image tags:** immutable, by commit SHA; `latest` only for convenience in dev.
- **Promotion:** the exact staging image is promoted to prod — no rebuild.
- **Eval gate:** block deploy if faithfulness/relevance drop below threshold.

---

## 7. Infrastructure as Code

- **Terraform** modules for: network, compute cluster, managed Postgres, object store,
  secrets, load balancer, DNS/TLS.
- Environments are reproducible and diffable; no click-ops in prod.
- State stored remotely (e.g., S3 + lock table) with per-env workspaces.

---

## 8. Configuration & Secrets

- Config via environment variables per stage (12-factor).
- Secrets in a cloud secrets manager (AWS Secrets Manager / Azure Key Vault / GCP Secret Manager),
  injected at runtime — never baked into images or committed.
- Rotate provider API keys on a schedule.

---

## 9. Scaling & Performance

- **Horizontal autoscaling** on API/UI by CPU and request latency.
- **Caching:** cache embeddings for repeated queries and hot documents; optional response
  cache for identical (question, profile) pairs.
- **Rate limiting** at the gateway to protect provider quotas and control cost.
- **Async ingestion** so bulk re-indexing runs off the request path.

---

## 10. Observability & Operations

- **Logs:** structured JSON (query → retrieved chunk ids → answer → feedback), centralized
  (CloudWatch/Stackdriver/Grafana Loki).
- **Metrics:** latency p50/p95, error rate, tokens + cost per query, retrieval hit rate.
- **Tracing:** `trace_id` propagated end-to-end for each interaction.
- **Alerts:** on error-rate spikes, latency breaches, cost anomalies, provider failures.
- **Dashboards:** operational (latency/cost) + quality (eval scores over time).

---

## 11. Security & Compliance

- TLS everywhere; HTTPS at the load balancer.
- Least-privilege IAM for compute → data/secret access.
- PII handling for uploads: scrub/flag, encrypt at rest and in transit, retention policy.
- Medical-education disclaimer surfaced in UI; no patient-specific clinical advice.
- Audit trail of which sources were used to answer (from interaction logs).

---

## 12. Rollout, Rollback & DR

- **Rollout:** start single-region, single-instance; enable autoscaling + managed vector DB
  as usage grows.
- **Strategy:** rolling or blue/green deploys; canary a small % of traffic for risky changes.
- **Rollback:** redeploy the previous immutable image tag (one step, since images are versioned).
- **Backups:** automated Postgres backups + point-in-time recovery; vector index re-buildable
  from source documents in object store.
- **DR:** documented restore runbook; periodic restore drills.

---

## 13. Deployment Checklist (per release)

- [ ] Tests + eval gate green in CI
- [ ] Images built and pushed (tagged by SHA)
- [ ] Secrets/config present for target env
- [ ] DB migrations applied
- [ ] Health checks passing post-deploy
- [ ] Dashboards/alerts show nominal latency, error, cost
- [ ] Rollback tag noted for quick revert
