# Medium Channel Info — Publishing Pattern

A reusable template and checklist for turning this RAG project into a Medium article.
Capture screenshots from the running app as you build, drop them into the marked slots,
and publish.

---

## 1. Article Metadata

| Field | Value |
|-------|-------|
| **Working Title** | Building a Personalized Learning RAG Assistant for Healthcare Exam Prep |
| **Subtitle** | How I used Design Thinking + RAG to make nursing exam prep adapt to each learner |
| **Author** | <your name> |
| **Publication** | <your Medium publication, or Personal> |
| **Estimated read time** | 8–12 min |
| **Canonical URL** | <fill after publish> |
| **Status** | Draft / Scheduled / Published |

### Suggested Tags (Medium allows 5)
`Artificial Intelligence` · `RAG` · `Machine Learning` · `Healthcare` · `Python`

### Alternate tag sets by angle
- Technical: `LLM`, `Vector Database`, `LangChain`, `FastAPI`, `Software Architecture`
- Product: `Product Design`, `Design Thinking`, `EdTech`, `Personalized Learning`, `AI`

---

## 2. The Reusable Article Pattern (Section-by-Section)

This is the skeleton. Each `>` note tells you what to write and where a screenshot goes.
Keep the narrative: **Problem → Thinking → Build → Deploy → Measure → Takeaways.**

### Hook / Intro (150–200 words)
> Open with the learner pain: a nervous first-timer and a top candidate get the same
> static textbook. State the one-line promise: a RAG assistant that is Grounded,
> Personalized, Pedagogical. Tease what the reader will learn.

### Section 1 — The Business Problem
> Paste the finalized problem statement. Keep it tight. Explain who it serves and the
> three pillars (Grounded / Personalized / Pedagogical).
>
> 📸 **SCREENSHOT SLOT 1:** the problem/architecture diagram.

### Section 2 — How Design Thinking Shaped It
> Walk the 5 stages (Empathize → Define → Ideate → Prototype → Test). Show how it turned
> "a chatbot over PDFs" into three measurable pillars.
>
> 📸 **SCREENSHOT SLOT 2:** a design-thinking stage diagram or whiteboard photo.

### Section 3 — High Level Design
> Drop the HLD architecture diagram and a 2–3 sentence tour of each layer
> (UI → API → Orchestration → Retrieval → Ingestion → Model → Storage).
>
> 📸 **SCREENSHOT SLOT 3:** HLD architecture diagram (from `docs/HIGH_LEVEL_DESIGN.md`).

### Section 4 — Low Level Design & Code Walkthrough
> Show the ingestion pipeline, the retrieval+rerank step, and the prompt templates
> (STAR / design-thinking scaffolding). Short code snippets only — link the repo for full code.
>
> 📸 **SCREENSHOT SLOT 4:** code snippet (ingestion or prompt template).
> 📸 **SCREENSHOT SLOT 5:** the running UI — upload a doc and ask a question.
> 📸 **SCREENSHOT SLOT 6:** a beginner answer vs. an advanced answer to the same question
> (this is the money shot that proves personalization).

### Section 5 — Design Patterns I Followed
> Summarize 4–5 key patterns (Strategy for providers, Factory, Pipeline, Repository,
> Template Method for prompts) and why. Link `docs/DESIGN_PATTERNS.md`.
>
> 📸 **SCREENSHOT SLOT 7:** a class/pattern diagram.

### Section 6 — Deployment
> Explain the container-first, cloud-agnostic approach and the CI/CD flow. Mention that
> the same containers run locally and in prod.
>
> 📸 **SCREENSHOT SLOT 8:** `docker compose up` terminal output or the CI/CD pipeline run.

### Section 7 — Evaluation & Results
> Three levels: retrieval (precision/recall, MRR), generation (faithfulness, relevance,
> citations via RAGAS/DeepEval), learning impact (level-fit, time-to-understanding,
> score lift). Share any numbers you have.
>
> 📸 **SCREENSHOT SLOT 9:** an evaluation dashboard or RAGAS score table.

### Section 8 — Lessons Learned & What's Next
> Honest reflection: what was hard (grounding discipline, personalization signal),
> what you'd do differently, and the roadmap (anatomy visualization phase).

### Call to Action
> Link the GitHub repo, invite claps/comments, ask readers what they'd personalize next.

---

## 3. Screenshot Capture Checklist

Capture these from the running app once the code is built:

- [ ] Slot 1 — Problem / architecture overview diagram
- [ ] Slot 2 — Design-thinking stages
- [ ] Slot 3 — HLD architecture diagram
- [ ] Slot 4 — Code snippet (ingestion / prompt template)
- [ ] Slot 5 — UI: upload document + ask question
- [ ] Slot 6 — Beginner vs advanced answer comparison (personalization proof)
- [ ] Slot 7 — Design-pattern / class diagram
- [ ] Slot 8 — `docker compose up` or CI/CD pipeline run
- [ ] Slot 9 — Evaluation results (RAGAS/DeepEval table)

### Screenshot tips for Medium
- Use a consistent window size and a clean light/dark theme.
- Crop tightly; hide secrets (`.env`, API keys, tokens) before capturing.
- Add short captions under each image — Medium shows them in a lighter font.
- Prefer PNG for UI/diagrams; keep width ~1400px for retina sharpness.
- Store originals in `docs/assets/medium/` so you can re-use them.

---

## 4. Pre-Publish Checklist

- [ ] Title and subtitle finalized (title ≤ 60 chars reads best in feeds)
- [ ] Cover image set (architecture diagram works well)
- [ ] All 9 screenshot slots filled with captions
- [ ] Code snippets syntax-highlighted (paste as Medium code blocks or embed GitHub Gists)
- [ ] Repo link added and repo is public
- [ ] Medical-education disclaimer included (no clinical/patient advice)
- [ ] No secrets or PII visible in any screenshot
- [ ] 5 tags chosen
- [ ] Proofread; read time 8–12 min
- [ ] Canonical URL set if cross-posting

---

## 5. Reusable One-Paragraph Summary (for the Medium "subtitle" / LinkedIn repost)

> I built a personalized learning RAG assistant for healthcare exam prep. It grounds every
> answer in trusted material, adapts the explanation to the learner's level, and structures
> teaching with frameworks like STAR and design thinking. Here's the architecture, the code,
> the deployment, and how I measured whether it actually helps people learn.

---

## 6. Publishing Log (fill as you go)

| Date | Action | Notes |
|------|--------|-------|
| | Draft started | |
| | Screenshots captured | |
| | Draft reviewed | |
| | Published | URL: |
