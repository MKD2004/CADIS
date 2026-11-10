# CADIS V2 — Checklist

Tick tasks off as they land. The plan and reasons behind each task are in
[`CADIS V2.md`](CADIS%20V2.md); the target layout is in [`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md);
the decisions are in [`DECISIONS.md`](DECISIONS.md).

**Legend:** `[x]` done · `[~]` partly done (see note) · `[ ]` not started

A phase is finished only when every **Done when** box is ticked (CADIS V2 §10: *"Finish each
phase with its 'done when' check before starting the next"*). When you tick something, also
update the status table in ARCHITECTURE_V2 §11.

---

## Phase 0 — Foundation  *(effort S–M)* — **done** (2026-11-10)

Committed as `4c57fab` → `a91a548`, docs in `68382dc`, evaluation set expanded in the commit after it. CI green on GitHub.

### Tasks

- [x] **0.1 Split `api_server.py`** into `backend/cadis/` without changing behaviour
  - [x] Package created: `api/`, `analysis/`, `answer/`, `ingest/`, `models/`
  - [x] V1 endpoints served from `api/legacy.py` (`/api/extract`, `/api/process`, `/api/qa-ask`) + `api/health.py`
  - [x] `api_server.py` is a shim (`from cadis.main import app`)
  - [x] All model loading goes through `models/registry.py`
  - [x] Dockerfile copies `backend/cadis` and runs `cadis.main:app`; `.dockerignore` added
  - [x] `benchmark.py` moved to `backend/scripts/`
- [x] **0.2 `config.py`** with pydantic-settings
  - [x] Magic numbers and model IDs moved to one `Settings` object (`CADIS_` prefix)
  - [x] V1 env names (`QA_MODEL`, `SUM_MODEL`, `NER_MODEL`, `EMB_MODEL`, `FRONTEND_URL`) still accepted
  - [x] No `os.getenv` outside `config.py`
  - [x] `pydantic-settings` added to `requirements.txt`
- [x] **0.3 Tests** (pytest)
  - [x] Unit tests with fake models (`tests/fakes.py`) — 73 pass in ~8 s
  - [x] Slow real-model tests behind `-m slow` (7 tests)
  - [x] Chunking covers every word · QA offsets match the text · summary chunks fit the model · endpoints return the right shape
  - [ ] `tests/integration/` tier (not needed until Phase 1 adds SQLite/ChromaDB)
- [x] **0.4 First evaluation set** (`data/eval/`)
  - [x] `backend/scripts/eval.py` — recall@k, MRR, EM/F1 per type, abstention, latency p50/p95
  - [x] 8 documents (~3,800 words, 28 passages): `climate`, `energy`, `legal`, `supply`, `medical`, `trial2`, `tech`, `operations` — pairs of related documents so cross-document and comparison questions exist
  - [x] 60 questions, 10 per type: single, numeric (incl. the pens example), cross-passage, cross-document, comparison, unanswerable
  - [x] Baseline saved: `data/eval/results/phase0.json` — recall@1 0.34 · recall@3 0.74 · recall@6 0.94 · MRR 0.86 · EM single 0.90, cross-passage 0.70, numeric 0.00, cross-document 0.20, comparison 0.20 · abstention 0.70
- [x] **0.5 Fix the problems from CADIS V2 §2.3**
  - [x] NER runs window by window (sentence-aligned, ≤ 400 tokens) and shifts offsets back (`analysis/ner.py`)
  - [x] Passages sized in embedding-model tokens and capped below MiniLM's 256 (`passage_tokens = 220`)
  - [x] Passage embeddings cached across `/api/process` → `/api/qa-ask` (`passage_cache`, LRU of 8 documents)
  - [x] No full n × n matrix: matrix capped at 20 sentences; top pairs found blockwise over all sentences
  - [x] PCA for the 2-D plot (backend `pca_2d` + `client/app/pipeline/embeddings/page.tsx`)
- [x] **0.6 CI** (GitHub Actions)
  - [x] `.github/workflows/ci.yml`: backend unit tests, `tsc --noEmit`, `npm run build`, pip-audit / npm audit (report only)
  - [x] Pushed; first run on `68382dc` succeeded

### Done when

- [x] Tests pass in CI (run on `68382dc`: success)
- [x] The evaluation script prints a baseline score for today's system
- [x] A long document's NER finds names on the last page — slow test `test_ner_reads_the_whole_long_document` passes locally with the real models (all 7 slow tests pass, 2026-11-10)

### Housekeeping before closing Phase 0

- [x] Commit the Phase 0 work in small Conventional Commits (ADR-027)
- [x] Add rows to `COMMIT_HISTORY.md`
- [x] Update ARCHITECTURE_V2 §11 status table
- [x] Update `README.md` (start command, benchmark path, settings, project tree)
- [x] Document `requirements-dev.txt` and how to run tests and eval (README §3)
- [x] `git push` and check the CI run

---

## Phase 1 — Ingestion and storage  *(effort L)* — **done** (2026-11-10)

Committed as `d870a4d` (storage) → `60e9bb2` (jobs) → `0051287` (ingest) → `42b48be` (API) → `2991521` (Library page).
All four **Done when** checks were run on a live server (results below).

### Tasks

- [x] **1.1 Database** — SQLite + SQLAlchemy 2 + Alembic (ADR-006)
  - [x] `storage/db.py` with WAL, `busy_timeout`, foreign keys on
  - [x] `storage/tables.py`: tenant, membership, collection, document, document_text, section, chunk, analysis_result, job, entity, mention (ARCHITECTURE_V2 §5)
  - [x] `storage/repositories.py` — every content query takes `allowed_collection_ids` (no default; `None` raises)
  - [x] `storage/files.py` — originals saved as `files/<sha256>`
  - [x] First Alembic migration in `backend/migrations/` (run at startup by `init_db`)
  - [x] `CADIS_DATA_DIR` / `CADIS_DATABASE_URL` settings; data dir in `.gitignore`
- [x] **1.2 Better parsing** (`ingest/parsers.py`, `parse_document`)
  - [x] PDF via PyMuPDF: text per page + font sizes and bold for headings (ADR-016)
  - [x] DOCX heading styles and tables in reading order; TXT blocks, form-feed pages, Markdown `#`
  - [x] Page number kept for every block, section and chunk
  - [ ] *(optional, later)* OCR with `ocrmypdf` for pages with no text layer — scanned PDFs currently fail with "no text found"
- [x] **1.3 Cleaning** (`ingest/cleaning.py`) — repeated headers/footers, page numbers, end-of-line hyphenation, line breaks inside sentences (list items kept), paragraphs split by a page break
- [x] **1.4a Section tree** (`ingest/sections.py`, ADR-028)
  - [x] Heading detection: DOCX heading styles; PDF font size / bold / numbering (`3.2 Dataset`); TXT short title lines followed by text
  - [x] `SECTION` rows with `parent_id`, `path` (`"3 Methodology > 3.2 Dataset"`), `level`, char range; deterministic IDs
  - [x] No headings → one root section (falls back to plain chunking)
  - [x] Unit tests: heading detection on the eval documents (`energy.txt` → Foreword, Targets, Generation, Storage, …)
- [x] **1.4 Chunking** (`ingest/chunking.py`)
  - [x] Counted in embedding-model tokens
  - [x] Chunks built *inside* each section; never cross a heading (overlap included); short section = one small chunk
  - [x] Cuts at sentence ends, preferring paragraph ends; over-long sentences cut at words
  - [x] `section_id` + `section_path` stored on every chunk, in Chroma metadata and in FTS5
  - [~] Size: **200 tokens max, 24 overlap** (not 300–500) because MiniLM reads only 256 tokens; the budget also shrinks per section so header + chunk always fit. The check runs at ingest time (needs the loaded model), not at app startup. Raise `CADIS_CHUNK_TOKENS` when Phase 2 moves to a 512-token model (ADR-011).
  - [x] `prev_id` / `next_id` links stored (small-to-big)
  - [x] Contextual header (`"Document › Section › Subsection"`) added before embedding
  - [x] Deterministic IDs: `sha1(document_id : version : ordinal)`
- [x] **1.5 Background jobs** (`jobs/states.py`, `jobs/queue.py`, `jobs/worker.py`, ADR-013)
  - [x] States `PENDING → PROCESSING → COMPLETED / FAILED`
  - [x] Atomic claim with lease (`locked_until`, `locked_by`); later updates fenced by owner
  - [x] Heartbeat thread extends the lease; handlers write stage + `progress`
  - [x] Recovery of expired leases at startup and every 30 s (lease 90 s, heartbeat 20 s)
  - [x] Retries up to `max_attempts`; `error` saved; permanent errors fail at once; manual retry from `FAILED`
  - [~] Progress stages: parsing → chunking → storing → embedding → indexing. The *analysis* stage comes with Phase 5.1.
  - [x] In-process worker started with the app
- [x] **1.6 Idempotent writes** (ADR-014)
  - [x] Upserts everywhere (SQLite `ON CONFLICT DO UPDATE`, ChromaDB `upsert`); FTS5 follows `chunk` through triggers in the same transaction
  - [x] Document versions: write new → flip `current_version` → delete old
  - [x] Write order: text + sections + chunks (+ FTS5) → ChromaDB → flip version → delete old → job `COMPLETED` last
  - [x] `backend/scripts/check_consistency.py` compares and repairs from SQLite (`--repair`)
- [x] **1.7 Access control in the data model** (ADR-015)
  - [x] Default tenant created on startup
  - [x] `collection_id` on every content row (document, section, chunk, vector metadata, entity); FTS rows join through `chunk`
  - [x] Retrieval requires allowed collection IDs: `retrieval/search.py` `dense_search` / `keyword_search(question, allowed_collection_ids, k, document_ids=None)`
  - [x] Allowed list computed server-side in `api/deps.py`, never from the request body
- [x] **1.8 New endpoints** (`api/collections.py`, `api/documents.py`, `api/jobs.py`, `api/schemas.py`)
  - [x] `POST /collections` · `GET /collections` · `GET /collections/{id}` · `GET /collections/{id}/documents`
  - [x] `POST /collections/{id}/documents` → `202` + `[{document_id, job_id, duplicate}]`
  - [x] `GET /documents/{id}` · `DELETE /documents/{id}` (removes text, sections, chunks, vectors, FTS rows, results, jobs)
  - [x] Extra: `GET /documents/{id}/sections`, `POST /documents/{id}/reingest`, `POST /jobs/{id}/retry`
  - [x] `GET /jobs/{id}` · `GET /jobs/{id}/events` (SSE)
  - [x] Errors use `{ "detail": … }` with real status codes (404, 409, 413, 415, 422, 503)
- [x] **1.9 Duplicate check** by file hash (same bytes in the same collection → existing document)
- [x] **Frontend:** Library page — collections, multi-file upload, live per-document status over SSE, section tree (`client/app/library/`, `client/lib/api.ts`)
- [x] **Tests:** `tests/integration/` with real SQLite + ChromaDB in a temp dir (crash recovery, tenant isolation); 156 tests in total

### Done when

- [x] Upload 20 PDFs of 100+ pages, close the browser, come back — all present with status "ready"
  — 20 generated PDFs × 105 pages, one upload (202 in 0.3 s): all READY after 73 s on a CPU laptop; 2,683 chunks; running headers and page numbers removed; ~71 sections per document found from fonts.
- [x] Kill the server mid-ingestion, restart — interrupted jobs finish by themselves with **no duplicate chunks or vectors**
  — killed at 51 % of embedding; after restart the job was recovered and finished on attempt 2; 243 chunk rows = 243 IDs = 243 FTS rows = 243 vectors, `check_consistency.py` clean. Also covered by `tests/integration/test_ingest_recovery.py` (crash at storing / embedding / indexing).
- [x] Deleting a document removes its chunks, vectors and BM25 entries — `test_delete_removes_chunks_vectors_fts_and_file`
- [x] Two-tenant isolation test passes — `tests/integration/test_tenant_isolation.py` (search + every endpoint)

Not part of the done-when, worth knowing: search over the 2,683 chunks took ~25 ms (dense) and ~7 ms (BM25) median.

---

## Phase 2 — Better retrieval  *(effort M)*

### Tasks

- [ ] **2.1 Embedding model upgrade** — compare MiniLM vs `bge-small-en-v1.5` vs `bge-base-en-v1.5` on the eval set; record result in ADR-011 (query instruction prefix for BGE; model ID stored with vectors)
  - [ ] If a 512-token model wins: raise `CADIS_CHUNK_TOKENS` (~384, now 200 for MiniLM) and re-ingest; the Chroma collection refuses a different model ID, so start a fresh data dir or re-index
- [ ] **2.2 Persistent vector store** (`index/vector_store.py`, ADR-007)
  - [ ] `VectorStore` interface + ChromaDB (embedded, on disk) implementation
  - [ ] One Chroma collection `chunks`, metadata `document_id`, `collection_id`, `version`, `page`
  - [ ] Every search filtered by allowed collections and current version
  - [ ] `index/exact.py` brute-force NumPy baseline; compare against ChromaDB on the eval set (ADR-012)
  - [ ] HNSW settings left at defaults unless measurements say otherwise
- [ ] **2.3 Keyword index** (`index/keyword_store.py`, ADR-008) — `KeywordStore` interface + SQLite FTS5; FTS5 enabled check at startup; `bm25()` sign converted
- [ ] **2.4 Hybrid search + RRF** (`retrieval/hybrid.py`, ADR-009) — top ~50 from each, `1 / (60 + rank)`
- [ ] **2.5 Cross-encoder re-ranker** (`retrieval/rerank.py`, ADR-010) — `ms-marco-MiniLM-L-6-v2`, keep top 6–8
- [ ] **2.6 Diversity** — MMR or per-document limit
- [ ] **2.6a Section soft filter** (`retrieval/sections.py`, ADR-028)
  - [ ] Resolve section names in the question against real section titles (fuzzy + title embedding; "Methods" ≈ "Methodology")
  - [ ] Run hybrid search with and without a `section_path` prefix filter; merge with RRF
  - [ ] Pass a small matched section whole to the answer model
  - [ ] No section named → plain hybrid search (no change in behaviour)
  - [ ] Add a **section-targeted** question type to the eval set (~10 questions) and report it in `eval.py`
- [ ] Small-to-big expansion with neighbour chunks (`retrieval/expand.py`)
- [ ] **2.7 Use new retrieval in extractive QA first**, to measure retrieval gain alone
- [ ] Add recall@8 to `eval.py` (`KS` is 1/3/6 today; the done-when below uses recall@8)
- [ ] Grow the eval collection toward the ~10,000-chunk latency target (e.g. add long PDFs once Phase 1 ingests them)
- [ ] Run `eval.py`, save `results/phase2.json`

### Done when

- [ ] recall@8 clearly higher than the Phase 0 baseline
- [ ] Section-targeted questions find evidence from *every* named section more often with the soft filter than without it (otherwise revisit ADR-028)
- [ ] A query over ~10,000 chunks returns in about 1 s on the Space's CPU

---

## Phase 3 — Generated answers with citations  *(effort M–L)*

**Decide first:** ADR-019 LLM provider (hosted vs local).

### Tasks

- [ ] **3.1 Choose the LLM** and put it behind `answer/llm.py` (`LLMClient`); `CADIS_LLM_*` settings; extractive mode when unset
- [ ] **3.2 Structured claims** (`answer/generative.py`)
  - [ ] Prompt with chunk IDs; JSON claims with citations + exact quotes (shape in CADIS V2 §5.4)
  - [ ] Rules: sources only, `not_in_documents`, one fact per claim, no arithmetic
  - [ ] Pydantic validation; one retry; fall back to extractive
- [ ] **3.3 Verification** (`answer/verify.py`, ADR-017)
  - [ ] Check 1 — quote exists in chunk (normalised, fuzzy, no new words) → char offsets
  - [ ] Check 2 — NLI entailment (`cross-encoder/nli-deberta-v3-base`) over all of a claim's quotes
  - [ ] Number rule: every number/date/amount appears in a quote or comes from the calculator
  - [ ] Failed claims removed or marked; status `partially_supported`
  - [ ] *(optional)* LLM evidence checker
- [ ] **3.4 Calculator** (`answer/calculator.py`, ADR-018)
  - [ ] Extract named values tied to quotes; check each value appears in its quote
  - [ ] LLM returns only the expression (`"a + b"`)
  - [ ] `ast`-based parser: numbers, `+ - * /`, brackets, sum/average/min/max/percent change — never `eval()`
  - [ ] `Decimal` for money; unit check and conversion (crore/lakh…); refuse if units don't match
  - [ ] `calculation` field with expression, inputs, result; citations for every input
- [ ] **3.5 Streaming** — `POST /query/stream` (SSE), one event per verified claim; also `POST /query`
- [ ] **3.6 Keep extractive mode** ("exact quote only") as an option
- [ ] **3.7 Update README** — "cannot hallucinate" only true for extractive mode; explain checks
- [ ] **Frontend:** Ask page with numbered citations (`client/app/ask/`)
- [ ] Trap-claim test set (e.g. the "20%" example)
- [ ] Run `eval.py`, save `results/phase3.json`

### Done when

- [ ] Numeric questions (pens example) answered correctly; every number comes from a quote or the calculator
- [ ] Cross-passage questions answered correctly most of the time
- [ ] Unanswerable questions return `not_in_documents`
- [ ] Every shown claim passes both checks
- [ ] Trap claims are caught by Check 2

---

## Phase 4 — Cross-document and multi-hop  *(effort L)*

### Tasks

- [ ] **4.1 Document filter** in API (`document_ids`) and UI
- [ ] **4.2 Query rewriting with chat history** (`history` in `/query`)
- [ ] **4.3 Query planner** (`retrieval/planner.py`)
  - [ ] Multi-hop: sub-questions + iterative retrieval
  - [ ] Comparison: retrieve per named document, then answer with both
  - [ ] Aggregation: map over documents, then reduce; limit + progress
  - [ ] Section-targeted: one sub-question per named section, soft section filter, quota per sub-question
- [ ] **4.4 Document summaries as routing layer** (needs Phase 5.6)
- [ ] **4.5 Entity index** queries over `ENTITY` / `MENTION` (needs Phase 5.4)
- [ ] **4.6** *(optional, only if eval shows need)* knowledge graph / GraphRAG
- [ ] **Frontend:** Viewer — click a citation → document at the right page with highlight (`client/app/documents/[id]/`)
- [ ] Run `eval.py`, save `results/phase4.json`

### Done when

- [ ] Multi-hop, comparison and section-targeted questions in the eval set pass at an agreed level
- [ ] Answers cite more than one document when they should

---

## Phase 5 — Rework the analysis modules  *(effort M, can run alongside Phases 2–4)*

### Tasks

- [ ] **5.1 Run once, store, serve by page** — analysis jobs after ingest → `ANALYSIS_RESULT`; `GET /documents/{id}/analysis/{module}?page=&page_size=`
- [ ] **5.2 Preprocessing** — whole-document stats; token details only for the viewed page/section
- [ ] **5.3 Embeddings view** — PCA/UMAP (PCA done in Phase 0), top pairs only, "chunks across the collection" view
- [ ] **5.4 NER**
  - [x] Chunk-by-chunk (done in Phase 0)
  - [ ] Keep entity positions for highlighting and linking
  - [ ] Split `MONEY`, `CARDINAL`, `PERCENT` into their own groups
  - [ ] Merge spellings of the same entity → fill `ENTITY` / `MENTION`
- [ ] **5.5 Ambiguity → coreference** (`analysis/coref.py`, ADR-025)
  - [ ] `fastcoref` (or `maverick-coref`); measure RAM
  - [ ] Display mention groups; highlight all mentions on click
  - [ ] Coref-enriched copy of text for embedding ("she [Sarah Johnson]")
  - [ ] Keep PP-attachment only as a labelled heuristic demo (or remove)
- [ ] **5.6 Summary** — run at ingest and store; per section → per document → per collection on request; LLM if available, DistilBART fallback
- [ ] **Frontend:** module pages load from the API, not `localStorage`

### Done when

- [ ] Every module works on a 200-page document without timeouts or huge responses
- [ ] Coreference view shows correct groups on the sample documents

---

## Phase 6 — Scale, deploy and harden  *(effort M)*

**Decide first:** ADR-020 production storage.

### Tasks

- [ ] **6.1 Persistence on HF Spaces** — paid storage, or Postgres + pgvector, or Postgres + Qdrant
- [ ] **6.2 Speed on CPU**
  - [ ] ONNX + int8 for embedding, re-ranker, NER (`optimum`)
  - [ ] Batched embedding; cache by text hash
  - [ ] Lazy loading; measure total RAM of all models
- [ ] **6.3 Limits and safety**
  - [ ] Max upload size and page count; reject files that are not really PDF/DOCX
  - [ ] Rate limiting per IP / user
  - [ ] Accounts, login, memberships and roles
  - [ ] Prompt-injection defences (document text wrapped as data, rules in system prompt)
- [ ] **6.4 Monitoring** — per-query timings, chunk IDs used, errors; a readable log or dashboard
- [ ] **6.5 Docs** — README and architecture for V2 with honest benchmark numbers
- [ ] Remove V1 endpoints and the `api_server.py` shim once nothing uses them (ADR-023)
- [ ] *(optional)* `import-linter` in CI for layer rules (ARCHITECTURE_V2 §4)

### Done when

- [ ] Deployed app keeps documents across restarts
- [ ] Handles several users at the same time
- [ ] A dashboard or log shows slow or failed queries

---

## Open decisions

| Decision | ADR | Needed by | Status |
|---|---|---|---|
| Embedding model (MiniLM / bge-small / bge-base) | 011 | Phase 2 | Proposed — decide by eval |
| LLM provider (hosted vs local) | 019 | Phase 3 | Open |
| Production storage | 020 | First deployed V2 with real data | Open |
| Coreference model | 025 | Phase 5 | Proposed |
