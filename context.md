# CADIS — Project Context

Working notes for anyone (human or AI) picking up this repository. Keep this file
updated as the project changes.

---

## 1. Hard Rules

These are non-negotiable conventions for this repo.

### 1.1 Git identity

Every commit **must** be authored by the repository owner. Never attribute commits to an
assistant, a bot, or a co-author.

- **Name:** `MKD2004`
- **Email:** `mahith.k@gmail.com`

The repo is already configured (`git config user.name` / `user.email`), so a plain
`git commit` is correct. Do **not** add `Co-Authored-By:` trailers, `Signed-off-by:`
lines, or "Generated with …" footers to commit messages or PR bodies.

If identity ever drifts, restore it with:

```bash
git config user.name  "MKD2004"
git config user.email "mahith.k@gmail.com"
```

### 1.2 Other conventions

- **Commit and push only when asked.** Do not push speculatively.
- **Verify before claiming.** ML changes must be run against a real document before being
  described as working. Install deps into `.venv/` (gitignored) rather than globally.
- **Keep the deployed surface in sync.** A model change in `api_server.py` must also be
  reflected in the `Dockerfile` pre-download step and in any frontend copy that names the
  model (`client/app/launch/page.tsx`, `client/app/pipeline/*/page.tsx`).
- **`localStorage` is the frontend's data bus.** `/launch` writes `cadis_document` (raw
  text) and `cadis_result` (the full `/api/process` payload); every `/pipeline/*` page
  reads from it. Changing a response key in `api_server.py` breaks the matching page.
- **Answer spans are character offsets into the raw document.** `start`/`end` must satisfy
  `document.slice(start, end) === answer` or the QA page highlights the wrong region.

---

## 2. Deployment Topology

| Layer | Host | Source | Notes |
|-------|------|--------|-------|
| Frontend | **Vercel** | `client/` | Next.js 15 App Router. Config in `client/vercel.json`. Needs `NEXT_PUBLIC_API_URL`. |
| ML Backend | **HuggingFace Spaces** | `Dockerfile` + `api_server.py` | Docker SDK, listens on `:7860`. Space card metadata in `hf_README.md`. |
| ML Backend (alt) | **Render** | same | Mirror of the HF Space. Whichever URL is in `NEXT_PUBLIC_API_URL` is the live one. |

There is **no API gateway**. The browser calls FastAPI directly; CORS is whitelisted in
`api_server.py` via the `FRONTEND_URL` env var plus hardcoded localhost origins.

---

## 3. File Map

### Root

| File | Purpose |
|------|---------|
| `api_server.py` | **The entire backend.** FastAPI app, model loaders, all six pipeline modules, four endpoints. |
| `Dockerfile` | HF Spaces image. Pre-downloads all models at build time so cold starts are fast. Copies only `api_server.py`. |
| `requirements.txt` | Python deps for the backend. |
| `hf_README.md` | YAML front-matter card for the HuggingFace Space. |
| `README.md` | Public-facing project documentation. |
| `context.md` | This file. |
| `data/ambiguity_dataset.csv` | Sample dataset. Not read at runtime. |

### `api_server.py` internals

| Section | Symbols | Notes |
|---------|---------|-------|
| Config | `ALLOWED_ORIGINS`, `QA_MODEL_ID`, `SUM_MODEL_ID`, `NER_MODEL_ID`, `EMB_MODEL_ID` | All model IDs are env-overridable. |
| Loaders | `get_nlp`, `get_embedder`, `get_ner_pipe`, `get_qa_pipe`, `get_summarizer` | `@lru_cache(1)` — lazy, loaded once per process. |
| QA engine | `_split_passages`, `_select_passages`, `_trim_span`, `_best_span`, `answer_question` | Retrieval → sliding-window → constrained span decode → null comparison. |
| Summarizer | `_sentence_chunks`, `_dedupe_sentences`, `_clean_summary`, `_generate`, `summarize_document` | Map-reduce over sentence-aligned chunks. |
| Modules | `run_preprocessing`, `run_embeddings`, `run_ner`, `run_ambiguity`, `run_qa`, `run_summary` | One per pipeline stage. |
| Endpoints | `/health`, `/api/extract`, `/api/process`, `/api/qa-ask` | |

Key constants: `QA_WINDOW=384`, `QA_STRIDE=128`, `MAX_ANSWER_TOKENS=40`, `QA_TOP_K=20`,
`MAX_PASSAGES=6`, `PASSAGE_WORDS=200`, `SUM_CHUNK_WORDS=400`, `MAX_SUM_CHUNKS=6`.

### `client/` (Next.js 15, App Router)

| Path | Purpose |
|------|---------|
| `app/page.tsx` | Landing page — composes the marketing components. |
| `app/layout.tsx` | Root layout, fonts, theme provider. |
| `app/globals.css` / `styles/globals.css` | Tailwind layers and custom animations. |
| `app/launch/page.tsx` | **Entry point of the app.** Upload / paste / sample picker, four bundled sample documents, the loading overlay, and the `/api/process` call. Writes `localStorage`. |
| `app/pipeline/layout.tsx` | Shared shell for the six module pages. |
| `app/pipeline/preprocessing/page.tsx` | Module 1 — token table, POS distribution, corpus stats. |
| `app/pipeline/embeddings/page.tsx` | Module 2 — similarity matrix, vector preview, 2-D scatter. |
| `app/pipeline/ner/page.tsx` | Module 3 — entity chips by type, SVO relation list. |
| `app/pipeline/ambiguity/page.tsx` | Module 4 — ambiguity cards with candidates and resolution. |
| `app/pipeline/qa/page.tsx` | Module 5 — 7 preset Q&As, custom question box, answer-span highlighting over the document. |
| `app/pipeline/summary/page.tsx` | Module 6 — executive summary, key sentences, timeline. |
| `components/navbar.tsx`, `hero.tsx`, `bento-grid.tsx`, `pricing.tsx`, `logo-marquee.tsx`, `final-cta.tsx`, `footer.tsx` | Landing page sections. |
| `components/pipeline-nav.tsx` | Step nav across the six module pages (`activeIndex` prop, 0–5). |
| `components/smooth-scroll.tsx`, `theme-provider.tsx` | Behaviour wrappers. |
| `components/ui/*` | shadcn/ui primitives. Generated — avoid hand-editing. |
| `lib/utils.ts` | `cn()` class-merge helper. |
| `hooks/use-mobile.ts`, `hooks/use-toast.ts` | UI hooks. |
| `vercel.json`, `next.config.mjs`, `tsconfig.json`, `postcss.config.mjs` | Build config. |

---

## 4. Known Rough Edges

Things that work but are not great. Not currently blocking.

- **Ambiguity module is heuristic theatre.** It flags a PP-attachment on nearly every
  sentence, `resolved` is chosen by cosine similarity between a single candidate *word* and
  its sentence, and `confidence` is that raw similarity (typically 0.2–0.4), which is not a
  meaningful probability. Anaphora detection rarely fires because the PP branch consumes
  the sentence first. Would need a real coreference model (e.g. `fastcoref`) to be honest.
- **`/api/process` is one blocking call**, ~30 s warm and slower on HF free-tier CPU. All
  six modules run whether or not the user visits every page. Streaming per-module results
  would make the loading overlay reflect reality instead of a 4-second timer.
- **`data/ambiguity_dataset.csv` is unused** at runtime.
- **No automated tests.** Verification is currently manual scripts run against sample docs.
- **First request after a cold start takes ~30 s** while models load into memory, despite
  the Dockerfile pre-download (that only warms the disk cache, not the process).

---

## 5. Change Log

Refinement pass — 2026-07-20.

### Phase 1 — QA engine (the "returns the whole document" bug)

**Root cause:** span decoding took an unconstrained `argmax` over the start and end logits
independently. Nothing forced `end >= start`, nothing restricted candidates to context
tokens, and nothing compared against the model's no-answer score. When the model was
unsure it put maximum start-probability on `[CLS]` (index 0) and end-probability hundreds
of tokens later, so `input_ids[0:end]` decoded to the question plus most of the document.
Reproduced on the deployed model: **3 of the 7 preset questions dumped the document**, one
returning a 1485-character "answer".

- [x] Constrain candidate spans to context tokens only (via `sequence_ids`), enforce
      `end >= start`, and cap length at `MAX_ANSWER_TOKENS`
- [x] Score spans as `start_logit + end_logit` over the top-20 candidates of each
- [x] Compare the best span against the `[CLS]` null score; return an empty answer when the
      model prefers "no answer"
- [x] Replace the meaningless softmax confidence with `sigmoid(best − null)`
- [x] Remove the `text[:2000]` truncation — content past ~350 words was previously
      unreachable, and questions about it returned wrong answers from earlier sections
- [x] Add sliding-window tokenization (384-token windows, 128-token stride) so answers
      spanning a boundary survive
- [x] Add MiniLM passage retrieval (top 6 of 200-word overlapping passages) to keep long
      documents fast
- [x] Batch every window of every passage into a single forward pass
- [x] Slice answers from the original text by character offset instead of decoding tokens —
      fixes lost casing and spacing (`dr. michael chen` → `Dr. Michael Chen`,
      `14. 2 months` → `14.2 months`) and makes frontend highlighting exact
- [x] Fix the offset mapping, which previously read offsets from the question sequence
- [x] Reuse one passage split across all 7 preset questions
- [x] Upgrade QA model `deepset/minilm-uncased-squad2` → `deepset/roberta-base-squad2`
      (the uncased model destroyed capitalization in every answer)
- [x] Route `/api/qa-ask` through the same engine instead of its own duplicated decode

**Result:** 6/7 preset questions answered at 0.89 average confidence, no document dumps,
all spans verified to satisfy `document[start:end] == answer`. Unanswerable questions
correctly return empty.

### Phase 2 — Summarization

**Root cause:** only the first 400 words were ever sent to DistilBART, so summaries
described the opening paragraphs and ignored the rest of the document.

- [x] Summarize the whole document via map-reduce instead of the first 400 words
- [x] Split chunks on sentence boundaries, evenly sized (`total / n_chunks`) so the last
      chunk isn't a stub that skews coverage
- [x] Add `length_penalty=2.0` and `no_repeat_ngram_size=3` to generation
- [x] Drop near-duplicate sentences across chunk summaries (content-word Jaccard with
      crude stemming) — beam search paraphrases the same fact per chunk
- [x] Clean detached punctuation (`cancer .` → `cancer.`) and trim summaries that stop
      mid-sentence
- [x] Scale summary length to document length instead of a fixed 90 tokens
- [x] Rank key sentences by entity/verb density **normalized for length**, then restore
      document order so they read as a narrative

**Result:** on a 689-word three-topic document, the summary now covers all three topics
(previously only the first); 124 words at 80% compression, no duplicated sentences.

### Phase 3 — Performance

- [x] Stop re-running the full spaCy pipeline on every sentence in the ambiguity module
- [x] Stop re-encoding the entire document per ambiguity candidate; score candidates
      against their own sentence instead (the old version compared every candidate in
      every sentence to the same whole-document vector, so rankings were meaningless)

### Phase 4 — Repository cleanup

- [x] Delete `ml-service/` — an unused second FastAPI backend (GLiNER/ChromaDB) that
      nothing deploys
- [x] Delete `modules/` — an unused Streamlit implementation importing a `ui_components`
      module that isn't in the repo
- [x] Delete `server/` — an unused Node/Express gateway; the frontend calls FastAPI directly
- [x] Delete the empty `newfrontend/` directory and stray `__pycache__/`
- [x] Rewrite `README.md`, which documented an architecture (Railway gateway, GLiNER,
      ChromaDB, React/Vite) that does not exist in this repo
- [x] Make all model IDs env-overridable (`QA_MODEL`, `SUM_MODEL`, `NER_MODEL`, `EMB_MODEL`)
- [x] Update the `Dockerfile` model pre-download to match the new QA model
- [x] Update frontend copy naming the QA model, and rewrite the confidence explainer
      (which told users 20–50% was normal — an artifact of the broken scoring)
- [x] Delete `client/lib/nlp-utils.ts` — dead client-side NLP fallback, confirmed unimported
- [x] Add `.venv/` to `.gitignore`
- [x] Write this file

### Not done / deferred

- [ ] Replace the heuristic ambiguity module with a real coreference model
- [ ] Stream per-module results from `/api/process` instead of one blocking response
- [ ] Add an automated test suite
