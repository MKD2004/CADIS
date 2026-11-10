# CADIS — Decision Log

This file records **why** CADIS uses each technology and design. Each entry is an
*Architecture Decision Record* (ADR).

**Why keep this file?** Code shows *what* we did. It does not show *why*, or what else we
considered. When something needs to change later, read the matching ADR first: it tells
you what problem the decision solved, so the change does not bring that problem back.

### How to use this file

- **Never delete an ADR.** If a decision changes, add a **new** ADR and mark the old one
  `Superseded by ADR-0xx`. The history of reasons is the whole point.
- **Status values:** `Accepted` (in force) · `Proposed` (planned, may change after
  measurement) · `Open` (needs a decision; a default is in force until then) ·
  `Superseded` · `Deprecated`.
- **Every ADR has a "Revisit if"** line — the signal that it is time to reconsider.
- Add the ADR in the same commit as the change it explains, and reference the ADR number
  in the commit message when useful.

Related: [`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md) (how it fits together) ·
[`CADIS V2.md`](CADIS%20V2.md) (phase plan) · [`COMMIT_HISTORY.md`](COMMIT_HISTORY.md).

---

## Index

| ADR | Decision | Status |
|---|---|---|
| [001](#adr-001--two-deployables-nextjs-frontend--fastapi-backend-no-gateway) | Two deployables: Next.js frontend + FastAPI backend, no gateway | Accepted |
| [002](#adr-002--python-311--fastapi-for-the-backend) | Python 3.11 + FastAPI for the backend | Accepted |
| [003](#adr-003--one-backend-package-split-into-layers-modular-monolith) | One backend package split into layers (modular monolith) | Accepted |
| [004](#adr-004--nextjs-app-router-on-vercel-for-the-frontend) | Next.js (App Router) on Vercel for the frontend | Accepted |
| [005](#adr-005--backend-on-hugging-face-spaces-docker-cpu-only-no-model-pre-download) | Backend on HF Spaces: Docker, CPU-only, no model pre-download | Accepted |
| [006](#adr-006--sqlite--sqlalchemy-2--alembic-for-relational-data) | SQLite + SQLAlchemy 2 + Alembic for relational data | Accepted |
| [007](#adr-007--chromadb-embedded-as-the-vector-store-behind-an-interface) | ChromaDB (embedded) as the vector store, behind an interface | Accepted |
| [008](#adr-008--sqlite-fts5-for-bm25-keyword-search) | SQLite FTS5 for BM25 keyword search | Accepted |
| [009](#adr-009--hybrid-retrieval-merged-with-reciprocal-rank-fusion) | Hybrid retrieval merged with Reciprocal Rank Fusion | Accepted |
| [010](#adr-010--cross-encoder-re-ranker) | Cross-encoder re-ranker | Accepted |
| [011](#adr-011--embedding-model) | Embedding model (bge-small-en-v1.5, pending measurement) | Proposed |
| [012](#adr-012--keep-an-exact-search-baseline-measure-before-tuning-hnsw) | Keep an exact-search baseline; measure before tuning HNSW | Accepted |
| [013](#adr-013--database-backed-job-state-machine-in-process-worker-first) | Database-backed job state machine; in-process worker first | Accepted |
| [014](#adr-014--idempotent-ingestion) | Idempotent ingestion | Accepted |
| [015](#adr-015--tenant-and-collection-scoping-from-day-one) | Tenant and collection scoping from day one | Accepted |
| [016](#adr-016--pymupdf-for-pdf-parsing) | PyMuPDF for PDF parsing | Accepted |
| [017](#adr-017--generated-answers-are-structured-claims-checked-twice) | Generated answers are structured claims, checked twice | Accepted |
| [018](#adr-018--the-llm-never-does-arithmetic) | The LLM never does arithmetic | Accepted |
| [019](#adr-019--llm-provider) | LLM provider | **Open** |
| [020](#adr-020--production-storage) | Production storage | **Open** |
| [021](#adr-021--configuration-with-pydantic-settings) | Configuration with pydantic-settings | Accepted |
| [022](#adr-022--testing-and-evaluation-strategy) | Testing and evaluation strategy | Accepted |
| [023](#adr-023--gradual-strangler-migration-from-v1) | Gradual ("strangler") migration from V1 | Accepted |
| [024](#adr-024--keep-extractive-qa-as-a-mode-and-as-the-highlighter) | Keep extractive QA as a mode and as the highlighter | Accepted |
| [025](#adr-025--replace-the-ambiguity-heuristic-with-coreference) | Replace the ambiguity heuristic with coreference | Proposed |
| [026](#adr-026--npm-is-the-only-frontend-package-manager) | npm is the only frontend package manager | Accepted |
| [027](#adr-027--git-workflow) | Git workflow | Accepted |
| [028](#adr-028--section-tree-as-a-soft-retrieval-filter) | Section tree as a soft retrieval filter | Accepted |

---

## ADR-001 — Two deployables: Next.js frontend + FastAPI backend, no gateway

- **Status:** Accepted · **Date:** 2026-07-20 (commit `7fa107a`), reaffirmed 2026-11-09

**Context.** In June 2026 CADIS had three backends: a Node/Express gateway (`server/`,
added in `7bab290`), a FastAPI ML service (`ml-service/`), and the older Streamlit
`modules/`. Only one was deployed. The README described an architecture the repo did not
run, and fixes went into code nothing used.

**Decision.** Exactly two deployables: the Next.js frontend and one FastAPI backend. The
frontend calls the backend directly. No API gateway.

**Why.**
- The ML work is in Python; a Node gateway only forwarded requests and added a second
  place for bugs, config and deployment.
- CORS, rate limiting and request validation can be done in FastAPI.
- One backend means one place to read, test and deploy.

**Alternatives.** Keep the Node gateway (rejected: extra hop and codebase for no
capability). Next.js API routes as a gateway (rejected for the same reason; also Vercel
function time limits are too short for ML calls).

**Consequences.** Backend URL is public; security (auth, limits) lives in FastAPI.

**Revisit if** several backend services exist (for example a separate GPU inference
service), or if one entry point for auth and routing becomes necessary.

---

## ADR-002 — Python 3.11 + FastAPI for the backend

- **Status:** Accepted · **Date:** 2026-06-30 (`8357e15`), reaffirmed 2026-11-09

**Context.** All models (spaCy, Hugging Face Transformers, sentence-transformers) are
Python libraries.

**Decision.** Python backend with FastAPI and Pydantic. Runtime target is **Python 3.11**
(the Dockerfile's `python:3.11-slim`). Code must also run on 3.12/3.13, which some
developer machines use.

**Why.**
- FastAPI gives typed request/response models (Pydantic), automatic OpenAPI docs, async
  for I/O, and Server-Sent Events for streaming answers and job progress.
- It was already in use; the team knows it.

**Alternatives.** Flask (no built-in validation or async), Django (too heavy for an API),
Node (would need a separate Python service for models anyway — see ADR-001).

**Consequences.** CPU-heavy model calls must not block the event loop: run them in sync
endpoints (FastAPI uses a thread pool) or in the job worker.

**Revisit if** the deployment base image changes Python version (update this ADR and the
Dockerfile together).

---

## ADR-003 — One backend package split into layers (modular monolith)

- **Status:** Accepted · **Date:** 2026-11-09

**Context.** V1 is one ~800-line file, `api_server.py`. V2 adds storage, jobs, indexes,
retrieval, an LLM and verification. In one file these would be impossible to test
separately.

**Decision.** One Python package, `backend/cadis/`, split by responsibility (`api`,
`ingest`, `index`, `retrieval`, `answer`, `analysis`, `models`, `storage`, `jobs`) with
one-way dependency rules (ARCHITECTURE_V2 §4). Still **one deployable** (a modular
monolith), not microservices.

**Why.**
- Each part can be unit-tested with fakes.
- External systems sit behind small interfaces (`VectorStore`, `KeywordStore`,
  `LLMClient`), so swapping one changes one file.
- One process keeps deployment on a single HF Space simple and shares loaded models
  between API and worker (models are the biggest memory cost).
- All model loading goes through `models/registry.py` (V1's `lru_cache` idea, in one
  place).

**Alternatives.** Keep one file (rejected: untestable at V2 size). Microservices
(rejected: more deployments, network calls and memory copies of models for no current
need).

**Consequences.** Layer rules must be kept by discipline (later: `import-linter` in CI).

**Revisit if** one part needs different hardware or scaling (e.g. GPU inference) — split
just that part into its own service.

---

## ADR-004 — Next.js (App Router) on Vercel for the frontend

- **Status:** Accepted · **Date:** 2026-06-30 (`67517eb`, `2aba8b2`; replaced a Vite +
  React app)

**Decision.** Next.js App Router, React 19, Tailwind, shadcn/ui, deployed on Vercel.
Pages are static and call the backend from the browser.

**Why.** File-based routing for the many pipeline pages, good Vercel integration, a large
component ecosystem (shadcn/ui), TypeScript.

**Consequences.**
- `next.config.mjs` has `typescript.ignoreBuildErrors: true`, so **`npm run build` does not
  type-check**. Run `npx tsc --noEmit` (CI will, ADR-022).
- Next.js 16 needs Node ≥ 20.9.
- Large results must not be stored in `localStorage` (about 5 MB limit; V1 hits 14 MB at
  ~10k words). V2 pages fetch from the API.

**Revisit if** server-side rendering of private data is needed (then server components +
auth on Vercel), or the frontend moves off Vercel.

---

## ADR-005 — Backend on Hugging Face Spaces: Docker, CPU-only, no model pre-download

- **Status:** Accepted · **Date:** 2026-07-20 (`ee58e66`)

**Decision.** The backend runs as a Docker Space on Hugging Face (port 7860). The image
installs **CPU-only torch first**, then `requirements.txt`, and bakes in the spaCy model.
**Model weights are not downloaded during the image build**; they download on first use.

**Why.**
- Free hosting with enough RAM for several transformer models.
- Installing CPU torch first stops pip from pulling ~2.5 GB of CUDA wheels.
- Pre-downloading weights pushed the build past the Spaces build timeout.

**Consequences.**
- The first request after a container start also downloads ~2.1 GB of weights (slow).
- **The container disk is not persistent** by default — see ADR-020.
- The Dockerfile in the repo must match what the Space builds. (It drifted once and
  would not have built — fixed in `ee58e66`.) Always change the repo's Dockerfile, never
  only the Space.

**Revisit if** cold starts become unacceptable, the app needs a GPU, or persistent
storage is needed (ADR-020).

---

## ADR-006 — SQLite + SQLAlchemy 2 + Alembic for relational data

- **Status:** Accepted · **Date:** 2026-11-09

**Context.** V2 must store tenants, collections, documents, chunks, jobs, analysis
results and entities.

**Decision.** SQLite file database, accessed through **SQLAlchemy 2.x** ORM, with schema
changes managed by **Alembic** migrations. Settings: WAL mode, `busy_timeout`, foreign keys
on.

**Why.**
- SQLite needs no server: one file, works in tests, locally and in the Space.
- It includes **FTS5**, which gives BM25 keyword search in the same database (ADR-008).
- SQLAlchemy keeps the code portable: moving to Postgres is mostly a connection-string
  change.
- Alembic makes schema changes repeatable instead of "delete the DB and start over".

**Alternatives.** Postgres from day one (more setup for development; may still be the
production choice — ADR-020). SQLModel (thin layer over SQLAlchemy; less control and
fewer docs for advanced use). Raw `sqlite3` (no migrations, no portability).

**Consequences.** SQLite allows one writer at a time — keep write transactions short.
FTS5 is SQLite-specific; the `KeywordStore` interface hides it.

**Revisit if** writes become frequent from several processes, or the deployment needs a
managed database (ADR-020).

---

## ADR-007 — ChromaDB (embedded) as the vector store, behind an interface

- **Status:** Accepted · **Date:** 2026-11-09

**History.** ChromaDB was used in the June 2026 `ml-service/` (`620d03d`). Its data folder
(`chroma_store/`) was committed to git by mistake and removed in `4431886`. The whole
service was deleted in `7fa107a` because nothing deployed it, and V1 used brute-force
search instead. That was right for single-document V1.

**Why it comes back now.** V2 stores many documents and must keep vectors between
requests and restarts, and filter search by collection and document. That needs a
persistent vector store.

**Decision.** ChromaDB in **embedded (persistent client) mode**, data under
`CADIS_DATA_DIR`, accessed only through `index/vector_store.py`. One Chroma collection
named `chunks`; vector ID = chunk ID; metadata `document_id`, `collection_id`, `version`,
`page`.

**Why ChromaDB.**
- Runs inside the Python process — no extra server on the Space.
- Persistent storage + metadata filtering out of the box.
- Builds an HNSW index automatically (ADR-012).
- Familiar from the earlier `ml-service`.

**Alternatives.** FAISS (fast, but no metadata filtering or persistence layer — we would
build them). pgvector (strong choice when Postgres is used — likely production option,
ADR-020). Qdrant (excellent filtering, but a separate server). LanceDB (embedded, good,
less familiar).

**Consequences.**
- ChromaDB and SQLite cannot share a transaction → write order and idempotency rules in
  ADR-014.
- **Never commit the data directory** (it is in `.gitignore`; the earlier mistake added
  hundreds of MB of binaries to git history).

**Revisit if** Postgres is adopted (then consider pgvector to have one store), or
filtering/latency measurements show a problem.

---

## ADR-008 — SQLite FTS5 for BM25 keyword search

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.** Keyword search uses an FTS5 virtual table in the same SQLite database,
ranked with FTS5's built-in `bm25()`.

**Why.** Embeddings miss exact strings (IDs, codes, rare names, "Section 12"). FTS5 gives
BM25 with no new dependency or service, and is updated in the same database as chunks.

**Alternatives.** `rank_bm25` / `bm25s` in memory (must be rebuilt on start, held in RAM).
Elasticsearch / OpenSearch (separate heavy service). Postgres full-text search (not true
BM25; option after ADR-020).

**Consequences.** FTS5's `bm25()` returns **lower = better** (negative numbers) — convert
before fusing. Check at startup that the SQLite build has FTS5 enabled.

**Revisit if** the database moves to Postgres (ADR-020).

---

## ADR-009 — Hybrid retrieval merged with Reciprocal Rank Fusion

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.** Run dense (ChromaDB) and keyword (FTS5) search, take the top ~50 of each,
and merge with **Reciprocal Rank Fusion**: `score = Σ 1 / (60 + rank)`.

**Why.** Dense and keyword search fail on different questions; combining them is more
robust than either. RRF uses ranks only, so the two very different score scales do not
need tuning or normalising.

**Alternatives.** Weighted score sum (needs normalisation and tuning per dataset). Dense
only (misses exact terms).

**Revisit if** evaluation shows a learned or weighted fusion is clearly better.

---

## ADR-010 — Cross-encoder re-ranker

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.** Re-rank the fused candidates with `cross-encoder/ms-marco-MiniLM-L-6-v2` and
keep the top ~8.

**Why.** A cross-encoder reads question and chunk together and ranks much better than
cosine similarity. The L-6 model is small enough for CPU on ~50 pairs per query.

**Alternatives.** `BAAI/bge-reranker-base` (more accurate, slower — first upgrade to try).
LLM re-ranking (slow and costly). No re-ranker (V1; lower precision).

**Revisit if** evaluation shows ranking errors in the top 8, or latency allows a larger
model.

---

## ADR-011 — Embedding model

- **Status:** Proposed · **Date:** 2026-11-09 · **Decided by:** Phase 2 evaluation

**Context.** V1 uses `all-MiniLM-L6-v2`, which reads at most **256 tokens** (a 200-word
passage is already ~244).

**Proposal.** `BAAI/bge-small-en-v1.5` (384-d, 512 tokens, similar speed to MiniLM).
Compare against MiniLM and `bge-base-en-v1.5` on the evaluation set before accepting.

**Consequences.**
- **Chunk size depends on this choice.** Chunks (plus the contextual header) must fit the
  embedding model's limit: ≤ 256 tokens for MiniLM, ≤ 512 for BGE.
- BGE expects a short instruction prefix on queries (not on documents).
- Changing the model means **re-embedding every chunk** — store the model ID with the
  vectors so a mismatch is detected.

**Revisit if** a better small model appears or multilingual documents are needed.

---

## ADR-012 — Keep an exact-search baseline; measure before tuning HNSW

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.** Keep a brute-force NumPy search (`index/exact.py`). Use it in tests and in
`eval.py` to compare ChromaDB's approximate (HNSW) results against exact ones. Leave HNSW
settings at defaults until measurements on our data show a problem.

**Why.** There is no fixed size where an approximate index starts to pay off; it depends
on vector size, hardware, concurrency, configuration and filtering. At CADIS's scale,
exact search is fast. ChromaDB is used for persistence and filtering (ADR-007); HNSW
comes with it. Do not optimise for a workload we do not have.

**Revisit if** recall vs exact search drops, or search latency grows with collection size.

---

## ADR-013 — Database-backed job state machine; in-process worker first

- **Status:** Accepted · **Date:** 2026-11-09

**Context.** Ingesting large documents takes minutes. If 20 jobs sit in an in-memory queue
and the server restarts, they are lost or stuck as "processing".

**Decision.** Jobs are rows in the `job` table with states
`PENDING → PROCESSING → COMPLETED / FAILED`. A worker **claims** a job with one atomic
update and a **lease** (`locked_until`), renews it with a heartbeat, and records
`attempts` and `error`. On startup and every minute, `PROCESSING` jobs with an expired
lease go back to `PENDING`. Execution starts as an **in-process worker** in the API
container.

**Why.** The database survives restarts, so no job is ever lost or stuck. Starting
in-process avoids running Redis and a second container on a free Space. Because state
lives in the table, moving execution to RQ or Celery later does not change the API or the
states.

**Alternatives.** FastAPI `BackgroundTasks` alone (lost on restart). Celery/RQ + Redis
now (extra services before they are needed).

**Revisit if** jobs need more parallelism than one container gives, or must run on
separate machines.

---

## ADR-014 — Idempotent ingestion

- **Status:** Accepted · **Date:** 2026-11-09

**Context.** Retries and lease recovery (ADR-013) mean a job **will** sometimes run twice.
SQLite, FTS5 and ChromaDB are separate stores with no shared transaction.

**Decision.**
- Deterministic chunk IDs: `sha1(document_id : version : ordinal)`.
- Every write is an **upsert** by ID (SQLite, FTS5, ChromaDB) — never a plain insert.
- Re-ingest writes a **new version**, flips `document.current_version` only when all
  writes succeed, then deletes the old version. Searches filter on the current version.
- Write order: SQLite chunks → FTS5 → ChromaDB → flip version → delete old →
  job `COMPLETED` **last**.
- `scripts/check_consistency.py` compares IDs across the three stores and repairs from
  SQLite (the source of truth).

**Why.** Running a job twice then gives the same final state as running it once, and a
crash in the middle never shows half-written data to searches.

**Revisit if** a single store holds everything (e.g. Postgres + pgvector with FTS) — then
real transactions can replace part of this.

---

## ADR-015 — Tenant and collection scoping from day one

- **Status:** Accepted · **Date:** 2026-11-09

**Context.** V2 starts single-user, but if access control is added later, one missed
filter lets one user retrieve another user's documents.

**Decision.**
- Every collection belongs to a tenant. Every document, chunk, vector, FTS row and entity
  stores its `collection_id`.
- Every function that reads document content **requires** `allowed_collection_ids`; there
  is no "all" default.
- The allowed list is computed on the server from the current tenant, never taken from the
  request body.
- The filter applies to every path: vector search, BM25, entity index, summary routing,
  caches (cache keys include collection IDs).
- Single-user mode = one default tenant. Phase 6 adds login on top; filtering already
  exists.
- An integration test with two tenants asserts that no query returns the other tenant's
  content.

**Why.** Isolation is a property of the data model, not a feature that can be bolted on.

**Revisit if** sharing rules become richer (per-document permissions) — extend
`membership`, keep the required filter.

---

## ADR-016 — PyMuPDF for PDF parsing

- **Status:** Accepted · **Date:** 2026-11-09

**History.** V1 uses `pypdf` (text only, no layout). The June 2026 `ml-service` used
`unstructured[pdf]`, which needs system packages (poppler, tesseract, libmagic) and a
layout model — heavy for a free Space with a build timeout (ADR-005).

**Decision.** **PyMuPDF** for PDFs: text per page, font sizes (to detect headings), fast,
pip-only. `python-docx` stays for DOCX. OCR (Tesseract via `ocrmypdf`) only as an optional,
later addition for pages with no text layer.

**Why.** Page numbers and headings are needed for citations and structure-aware chunking;
`pypdf` does not give them reliably. PyMuPDF does, without system packages.

**Licence note.** PyMuPDF is **AGPL-3.0** (or a paid commercial licence). This is fine
for an open-source, academic project, but if CADIS ever becomes closed-source or a paid
hosted service, switch to `pypdfium2` (Apache/BSD) or buy a licence. The parser sits
behind `ingest/parsers.py`, so the switch is contained.

**Alternatives.** Docling (strong on tables, heavier — consider for table-heavy documents).
`unstructured` (see history). `pypdfium2` (permissive licence, less layout information).

**Revisit if** licence terms matter, or many documents are scanned or table-heavy.

---

## ADR-017 — Generated answers are structured claims, checked twice

- **Status:** Accepted · **Date:** 2026-11-09

**Context.** Checking only that a quoted sentence exists is not enough: the model can
quote a real sentence ("revenue of ₹50 crore in 2025") under a claim it does not support
("revenue increased by 20%").

**Decision.**
- The LLM returns **JSON claims** (one fact each), each with `chunk_id` citations and an
  exact quote, validated with Pydantic. Invalid JSON → one retry → extractive fallback.
- **Check 1 — quote validation:** the quote exists in the cited chunk (normalised, small
  fuzzy tolerance, no new words); store its character offsets.
- **Check 2 — claim validation:** an NLI model (start: `cross-encoder/nli-deberta-v3-base`)
  must judge the quotes as *entailing* the claim, **and** every number/date/amount in the
  claim must appear in a quote or come from the calculator (ADR-018).
- Claims that fail are removed or shown as unsupported; the answer becomes
  `partially_supported`.
- These checks are a **quality filter, not a guarantee**; the UI always links to the
  source.

**Why.** Per-claim structure makes each fact checkable; two checks catch both invented
quotes and misused real quotes.

**Revisit if** the NLI model's error rate on our trap-claim tests is too high (try a larger
NLI model or an LLM verifier).

---

## ADR-018 — The LLM never does arithmetic

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.** The LLM extracts numeric inputs (each tied to a quote) and chooses the
operation as an expression over named values (`"a + b"`). A **deterministic calculator**
in Python evaluates it: `ast`-based parser allowing only numbers, `+ - * /`, brackets and a
small set of functions (sum, average, min, max, percent change); **never `eval()`**;
`Decimal` for money; units checked and converted first (crore/lakh, etc.), and no
calculation if units cannot be matched. The result is returned with citations for every
input.

**Why.** LLMs make arithmetic slips that look confident. Python arithmetic is exact,
testable and explainable.

**Revisit if** questions need maths beyond the allowed functions — extend the function
list, keep evaluation in Python.

---

## ADR-019 — LLM provider

- **Status:** **Open** · **Date:** 2026-11-09 · **Needed by:** Phase 3

**Current default.** No LLM configured → **extractive mode only** (V1 behaviour). All code
calls the LLM through `answer/llm.py` (`LLMClient` interface), so the choice does not
affect other code.

**Options.**

| | Hosted API (e.g. Claude Haiku / Sonnet) | Local model (1.5B–3B instruct, quantized, `llama.cpp`) |
|---|---|---|
| Quality / reasoning | High | Lower |
| Speed on a free CPU Space | Fast | Several to tens of seconds per answer |
| Cost | Per request | Free |
| Privacy | Document text sent to the provider | Stays on the server |
| Ops | API key, rate limits | Extra RAM (~2 GB+), model download |

**Leaning:** hosted for quality and a smooth demo, keeping a local implementation of the
same interface. Record the final choice here (change status to Accepted) before Phase 3.

---

## ADR-020 — Production storage

- **Status:** **Open** · **Date:** 2026-11-09 · **Needed by:** first deployed V2 with
  real data

**Problem.** The HF Space disk is wiped on restart (by default), so a SQLite file and
ChromaDB folder there would lose all documents.

**Current default.** Development and demos use local disk (`CADIS_DATA_DIR`); deployed
data is treated as temporary.

**Options.**
1. Paid persistent storage on the Space (keep SQLite + Chroma as is).
2. Managed Postgres with **pgvector** (one service for tables, vectors and full-text) —
   replaces ADR-006/007/008 in production via the existing interfaces.
3. Managed Postgres + hosted Qdrant.

**Leaning:** option 2. Check current prices and free-tier limits before deciding.

---

## ADR-021 — Configuration with pydantic-settings

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.** One `Settings` class in `cadis/config.py` (pydantic-settings). All variables
use the `CADIS_` prefix; `.env` supported in development. V1 names (`QA_MODEL`,
`SUM_MODEL`, `NER_MODEL`, `EMB_MODEL`, `FRONTEND_URL`) are read as fallbacks until the
migration ends. No `os.getenv` anywhere else.

**Why.** Typed, validated settings in one place; tests override settings easily; V1
deployments keep working.

**Revisit if** secrets management needs a vault or the platform injects config
differently.

---

## ADR-022 — Testing and evaluation strategy

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.**
- **pytest** with three levels: `unit` (fake models, milliseconds), `integration` (real
  SQLite + ChromaDB in a temp folder), `slow` (real models; skipped unless `-m slow`).
- **Evaluation** (`scripts/eval.py`) on `data/eval/`: recall@k, MRR, answer accuracy,
  faithfulness, abstention, latency — results saved per phase.
- **CI** (GitHub Actions): unit + integration tests, `npx tsc --noEmit`, `npm run build`,
  and `npm audit` / `pip-audit` (report, then decide — not every advisory affects us).

**Why.** V1 had no tests; several real bugs (QA span decoding, summary truncation, NER
truncation, highlight offsets) were found only by reading code. Fake models keep tests
fast enough to run on every commit.

**Revisit if** CI gets slow — split jobs or cache models.

---

## ADR-023 — Gradual ("strangler") migration from V1

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.** Move V1 code into the package without behaviour changes first, serve the V1
endpoints from `api/legacy.py`, keep `api_server.py` as a one-line shim, add V2 endpoints
beside them, migrate the frontend page by page, then remove V1 endpoints.

**Why.** The deployed app keeps working at every commit; any regression is traceable to a
small step (see COMMIT_HISTORY.md).

**Revisit if** keeping V1 alive blocks a needed change — remove the specific endpoint
deliberately, in its own commit.

---

## ADR-024 — Keep extractive QA as a mode and as the highlighter

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.** `deepset/roberta-base-squad2` and the V1 span decoder stay: as an
"exact quote only" answer mode, as the fallback when no LLM is configured or the LLM
output is invalid, and to locate supporting spans for highlighting.

**Why.** It is fast, cannot invent text, and its span decoding is already fixed and
tested in practice (`7fa107a`, `fab64bf`, `adf0eeb`).

**Revisit if** a single model can both generate and reliably point to spans.

---

## ADR-025 — Replace the ambiguity heuristic with coreference

- **Status:** Proposed · **Date:** 2026-11-09 · **Phase:** 5

**Context.** The V1 module flags nearly every sentence with a preposition as "PP
attachment", and its "resolution" compares a sentence embedding with single-word
embeddings — which does not find what a pronoun refers to.

**Proposal.** A coreference model (`fastcoref` first; `maverick-coref` if accuracy is
needed). Use the mention clusters for display and to enrich text before embedding
("she [Sarah Johnson]"). Keep the V1 heuristic only as a clearly labelled teaching demo.

**Revisit if** the coref model's memory/latency does not fit the Space — then run it only
on demand.

---

## ADR-026 — npm is the only frontend package manager

- **Status:** Accepted · **Date:** 2026-11-09 (`76c0e6c`)

**Decision.** `client/package-lock.json` is the only lockfile; `vercel.json` installs with
`npm install`.

**Why.** A stale `pnpm-lock.yaml` still pinned versions with known vulnerabilities (Next
16.0.10, zod). Two lockfiles drift; one does not.

**Revisit if** the team switches to pnpm — then delete `package-lock.json` in the same
commit and update `vercel.json`.

---

## ADR-027 — Git workflow

- **Status:** Accepted · **Date:** 2026-11-09

**Decision.**
- Single maintainer → commit directly to `main`.
- Commit messages follow **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`,
  `refactor:`, `test:`, `ci:`), with a body explaining *why* for anything non-trivial.
- Each commit is one logical change, and the app should work at every commit (so
  `git bisect` and `git revert` are useful).
- `COMMIT_HISTORY.md` is updated with each new commit (see that file for the rule).
- Never commit generated data, model weights, `node_modules/`, database or vector-store
  files (both happened before: `44cb38d`, `620d03d`, cleaned up in `4431886`).

**Revisit if** more contributors join — switch to feature branches and pull requests with
CI required.

---

## ADR-028 — Section tree as a soft retrieval filter

- **Status:** Accepted · **Date:** 2026-11-10 · **Measured by:** Phase 2 and Phase 4 evaluation

**Context.** Many questions point at parts of a document by name: *"Find the dataset
information from Methodology and the experimental results from Experiments."* With a flat
list of chunks, both halves of the question compete for the same top 8, one section
usually wins, and the other half goes unanswered. Chunks that span two headings also mix
two topics, which blurs their embedding and can put unrelated facts side by side in front
of the answer model.

An option we considered: replace vector search with a **tree walk**, like folders on a disk
(document → section → subsection → chunks), letting the system pick a folder and read only
what is inside.

**Decision.** Keep hybrid search (HNSW dense + BM25, ADR-009) as the engine, and add the
**section tree as structure around it**:

1. **Ingest builds a section tree** from headings (DOCX heading styles; PDF font size,
   bold and numbering such as `3.2 Dataset`; TXT short title lines followed by a blank
   line). It is stored in a `SECTION` table (`parent_id`, `path`, `level`, char range).
2. **Chunks never cross a section boundary.** A short section becomes one small chunk
   instead of being merged with its neighbour; overlap does not cross headings either.
   Each chunk stores `section_id` and `section_path` (`"3 Methodology > 3.2 Dataset"`),
   also in ChromaDB metadata and FTS5. Text with no headings falls back to paragraph and
   sentence cuts.
3. **Section targets are a soft filter, not a hard one.** When a question (or a
   sub-question from the planner) names a section, the name is resolved against the real
   section titles (fuzzy match + title embedding, so "Methods" ≈ "Methodology"). Search
   then runs **with** the section filter and **without** it, and the two lists are merged
   with RRF, so in-section chunks rank higher but out-of-section chunks can still appear.
4. **Quota per sub-question:** each sub-question gets its share of the final slots, so
   one section cannot fill the whole context.
5. **Whole-section expansion:** if a matched section is small, its full text is given to
   the answer model (parent-document version of small-to-big).
6. **No section named → plain hybrid search.** The query planner decides which path a
   question takes: simple name matching from Phase 2, LLM sub-question planning from
   Phase 4.

**Why.**
- **Speed is not the gain.** At ~10,000 chunks, HNSW and even brute force are
  milliseconds, and one section is only tens of chunks. What structure buys is *precision
  and coverage* on questions with several targeted parts, and cleaner chunks.
- **A hard tree walk fails silently.** If the folder is wrong ("dataset" is in
  "4.1 Experimental Setup", not "Methodology"; another paper says "Methods"), the answer
  can never be found. Tree walks done by an LLM also cost one call per level, and errors
  compound. The soft filter keeps the precision and removes the dead end.
- **Most questions name no section**, so global search must stay the default.
- Section paths in the contextual header (`"Doc › Section: …"`) also help dense and BM25
  ranking for ordinary questions.

**Alternatives.**
- *Pure tree navigation* (LLM walks the table of contents) — rejected for the reasons above.
- *Hard metadata filter only* — rejected: no recovery when the label is wrong.
- *Flat chunks only* (no structure) — rejected: mixed-topic chunks, crowding on
  multi-part questions.
- *Section summary nodes* (RAPTOR-style: index title + short summary per section) —
  deferred; add only if the evaluation shows broad "what does section X say" questions
  failing.
- *Semantic chunking* (split where neighbouring-sentence similarity drops) — deferred;
  only for long sections without headings, and only if it measurably helps.

**Consequences.**
- New `SECTION` table and `section_id` / `section_path` on `CHUNK`, Chroma metadata and
  FTS5 (ARCHITECTURE_V2 §5).
- Heading detection is heuristic for PDF/TXT; bad headings degrade to plain hybrid
  search, never to lost answers.
- A new evaluation question type, **section-targeted**, tracks this.

**Revisit if** section-targeted questions do no better than plain hybrid search on the
evaluation set (then drop the filtered search and keep only clean chunking), or if the
soft boost lets too many out-of-section chunks through (then make the filter harder when
the section match is very confident).

---

## Lessons from the commit history

These shaped several decisions above. Hashes refer to `COMMIT_HISTORY.md`.

| Lesson | Evidence | Now enforced by |
|---|---|---|
| Unused backends and docs drift from reality | 3 backends, 1 deployed; README described another architecture (`7fa107a`, `094f86f`) | ADR-001, ADR-023 |
| Deployment config drifts from the repo | Dockerfile in repo would not build (`ee58e66`) | ADR-005 |
| Dependencies and data committed to git | `node_modules` (903 files, `44cb38d`) and `chroma_store` (`620d03d`), removed in `4431886` | ADR-007, ADR-027 |
| Library upgrades break silently | transformers v5 broke the QA pipeline (`30983f7`) | ADR-022 (tests), pinned floors |
| Correctness bugs hide without tests | QA decoding (`7fa107a`), sliding window never firing (`fab64bf`), summary tail loss + highlight offsets (`adf0eeb`) | ADR-022 |
| Unused packages with known vulnerabilities | `9d4a164`, `76c0e6c`, `5a7ef48` | ADR-026, CI audit |
