# CADIS — Context-Aware Document Intelligence System

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Spaces-FFD21E?style=flat-square&logo=huggingface&logoColor=black)
![Vercel](https://img.shields.io/badge/Vercel-Frontend-000000?style=flat-square&logo=vercel&logoColor=white)

A document intelligence platform that runs a six-module NLP pipeline over any PDF, DOCX or
pasted text — preprocessing, sentence embeddings, named entity recognition, ambiguity
resolution, extractive question answering and abstractive summarization — and walks you
through each stage in an interactive Next.js dashboard.

> **CADIS V2 is in progress.** V2 turns CADIS from a single-document demo into a system
> that stores **many large documents** and answers questions **across** them, with cited,
> checked answers. Phase 0 (foundation) is done; the running app is still V1.
> Jump to [CADIS V2](#cadis-v2--many-documents-cited-answers) for the design and roadmap.

---

## CADIS V2 — many documents, cited answers

### What changes

| | V1 (today) | V2 (target) |
|---|---|---|
| Documents | Sent with every request, never stored | Uploaded once into **collections**, stored and processed in background jobs |
| Scope | One document at a time | Questions across a whole collection |
| Chunks | Fixed-size passages that ignore headings | **Section-aware chunks**: never cross a heading, each knows its section path |
| Search | Brute-force MiniLM cosine | **Hybrid**: dense vectors (ChromaDB/HNSW) + BM25 (SQLite FTS5), fused with RRF, re-ranked by a cross-encoder, with a **soft section filter** |
| Answers | Extractive span (RoBERTa) | **Structured claims** written by an LLM, each with a citation and an exact quote, checked twice (quote match + entailment) |
| Arithmetic | Not possible | The LLM writes the expression; **Python computes it** (Decimal, unit checks) |
| Storage | None | SQLite (metadata, chunks, jobs, FTS5) + ChromaDB (vectors) + file store |

### How a document is ingested

```mermaid
flowchart LR
    UP["Upload<br/>PDF / DOCX / TXT"] --> JOB["Background job<br/>(lease, retries, progress)"]
    JOB --> PARSE["Parse + clean<br/>pages, headers/footers"]
    PARSE --> TREE["Section tree<br/>from headings"]
    TREE --> CH["Chunk inside each section<br/>300–500 tokens, never crosses a heading"]
    CH --> HDR["Contextual header<br/>Doc › Section: …"]
    HDR --> IDX["Index<br/>SQLite + FTS5 + ChromaDB<br/>(idempotent upserts)"]

    style TREE fill:#111827,stroke:#22d3ee,color:#e2e8f0
```

Documents keep their structure as a **section tree**, like folders on a disk:

```
Paper.pdf
├── 3 Methodology
│   └── 3.2 Dataset        ← chunks here carry section_path "3 Methodology > 3.2 Dataset"
└── 4 Experiments
    └── 4.2 Results
```

Because a chunk never spans two sections, one chunk is about one topic.

### How a question is answered (proposed flow)

```mermaid
flowchart TB
    Q["Question"] --> PLAN["Query planner<br/>rewrite with chat history<br/>split multi-hop / comparison / section-targeted"]
    PLAN --> SEC{"Names a section?"}
    SEC -- "no" --> HY["Hybrid search<br/>dense (HNSW) + BM25 → RRF"]
    SEC -- "yes" --> RES["Resolve against real section titles<br/>'Methods' ≈ 'Methodology'"]
    RES --> SOFT["Hybrid search with AND without<br/>the section filter → RRF<br/>(in-section chunks rank higher)"]
    HY --> RR["Cross-encoder re-rank → top 8<br/>quota per sub-question"]
    SOFT --> RR
    RR --> EXP["Expand: neighbour chunks,<br/>or a small section in full"]
    EXP --> LLM["LLM → JSON claims<br/>each with chunk ID + exact quote"]
    LLM --> CALC["Calculator<br/>(Python, not the LLM)"]
    CALC --> CHK["Check 1: quote is in the chunk<br/>Check 2: quote entails the claim"]
    CHK --> OUT["Answer with citations<br/>answered / partially supported / not in documents"]

    style SEC fill:#111827,stroke:#22d3ee,color:#e2e8f0
    style SOFT fill:#111827,stroke:#22d3ee,color:#e2e8f0
```

**Why the section filter is soft.** For *"Find the dataset information from Methodology and
the experimental results from Experiments"*, the planner makes two sub-questions, one per
section, and each gets its own share of the final chunks so one section cannot crowd out
the other. Search still runs over everything too, so if the dataset details actually sit
in *Experimental Setup*, they are not lost. Questions that name no section use plain
hybrid search. HNSW stays the search engine; the tree guides it
([ADR-028](DECISIONS.md#adr-028--section-tree-as-a-soft-retrieval-filter)).

### Roadmap

| Phase | Goal | Status |
|---|---|---|
| 0 — Foundation | Package split, config, tests, evaluation set, CI, V1 scale fixes | ✅ Done |
| 1 — Ingestion and storage | Stored collections, background jobs, section tree, section-aware chunking, tenancy | Next |
| 2 — Better retrieval | Better embeddings, ChromaDB + BM25 hybrid, re-ranker, section soft filter | Planned |
| 3 — Generated answers | LLM claims with citations, two checks, Python calculator | Planned |
| 4 — Cross-document | Query planner: multi-hop, comparison, section-targeted sub-questions | Planned |
| 5 — Analysis rework | Stored per-document results, coreference, entity index | Planned |
| 6 — Scale and deploy | Persistent storage, ONNX on CPU, auth, limits, monitoring | Planned |

### Measuring progress

Every phase is measured on the same evaluation set in `data/eval/`: 8 documents and 60
questions, 10 each of single-fact, numeric, cross-passage, cross-document, comparison and
unanswerable (section-targeted questions are added in Phase 2). Phase 0 baseline with V1
retrieval and extractive QA (`data/eval/results/phase0.json`):

| Metric | Phase 0 |
|---|---|
| Recall@1 / @3 / @6 | 0.34 / 0.74 / 0.94 |
| MRR | 0.86 |
| Exact match: single-fact / cross-passage | 0.90 / 0.70 |
| Exact match: numeric / cross-document / comparison | 0.00 / 0.20 / 0.20 |
| Unanswerable questions correctly declined | 0.70 |
| Latency median / p95 | 1.7 s / 2.0 s |

Numeric, cross-document and comparison questions are what V2's later phases target.

**V2 documents:** [`CADIS V2.md`](CADIS%20V2.md) (phase plan and the ideas behind it) ·
[`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md) (components, data model, flows) ·
[`DECISIONS.md`](DECISIONS.md) (why each choice was made) ·
[`CHECKLIST.md`](CHECKLIST.md) (task progress) ·
[`COMMIT_HISTORY.md`](COMMIT_HISTORY.md) (what changed when).

---

## Current release (V1)

The rest of this README describes the version that runs today.

## Architecture

```mermaid
flowchart LR
    subgraph Client ["Frontend — Vercel"]
        UI["Next.js 16 / React 19<br/>Tailwind / Framer Motion"]
    end

    subgraph ML ["ML Backend — HuggingFace Spaces (Docker)"]
        API["FastAPI — cadis package<br/>backend/cadis"]
        subgraph Models ["NLP Models"]
            SPACY["spaCy en_core_web_sm<br/>Tokens · POS · Deps · Sents"]
            MiniLM["all-MiniLM-L6-v2<br/>384-d Embeddings"]
            BERT["dslim/bert-base-NER<br/>Entity Recognition"]
            RoBERTa["roberta-base-squad2<br/>Extractive QA"]
            BART["distilbart-cnn-12-6<br/>Summarization"]
        end
    end

    UI -- "POST /api/extract" --> API
    UI -- "POST /api/process" --> API
    UI -- "POST /api/qa-ask" --> API
    API --> SPACY
    API --> MiniLM
    API --> BERT
    API --> RoBERTa
    API --> BART

    style Client fill:#0d1117,stroke:#22d3ee,color:#e2e8f0
    style ML fill:#0d1117,stroke:#34d399,color:#e2e8f0
    style Models fill:#111827,stroke:#475569,color:#e2e8f0
```

There is no separate API gateway — the frontend calls FastAPI directly, with CORS
restricted to localhost plus the origins in `CADIS_FRONTEND_URLS` (or the V1 `FRONTEND_URL`).

### Request Flow

1. **Upload** — the user drops a `.pdf` / `.docx` / `.txt` file (or pastes text, or picks
   a bundled sample) on `/launch`
2. **Extract** — `POST /api/extract` parses `.pdf` / `.docx` files with `pypdf` /
   `python-docx` and returns plain text (`.txt` files are read directly in the browser)
3. **Process** — `POST /api/process` runs all six modules in one call and returns a single
   JSON payload
4. **Explore** — the result is cached in `localStorage` and rendered across six pages under
   `/pipeline/*`, one per module
5. **Ask** — on the QA page, `POST /api/qa-ask` answers arbitrary follow-up questions
   against the same document

---

## The Six Modules

| # | Module | Model | What it produces |
|---|--------|-------|------------------|
| 1 | **Preprocessing** | spaCy `en_core_web_sm` | Tokens with lemma/POS/dependency, sentence split, corpus stats |
| 2 | **Embeddings** | `all-MiniLM-L6-v2` | 384-d sentence vectors, similarity matrix for the first 20 sentences, most-similar pairs across all sentences, PCA 2-D map |
| 3 | **NER + IE** | `dslim/bert-base-NER` + spaCy | Person/Org/Location/Misc entities (BERT, run in sentence-aligned windows so long documents are read to the end) plus Date and numeric entities (spaCy — the "Money" bucket also holds cardinals and percentages), subject-verb-object relations |
| 4 | **Ambiguity** | MiniLM + spaCy parse | PP-attachment and anaphoric ambiguities (at most one per sentence), each with a resolved candidate |
| 5 | **QA Engine** | `deepset/roberta-base-squad2` | Extractive answer spans with character offsets and confidence |
| 6 | **Summary** | `sshleifer/distilbart-cnn-12-6` | Abstractive executive summary, key sentences, date-anchored timeline |

### How QA works

Extractive QA returns a span of your document — it never generates text, so it cannot
hallucinate. Getting a *correct* span requires more than an argmax:

- The document is split into overlapping passages of at most 220 **embedding-model
  tokens** (50-token overlap), so each passage fits inside MiniLM's 256-token limit and
  nothing is cut off before embedding. MiniLM ranks them against the question and the
  top 6 go to the model. Long documents stay answerable without running the QA model over
  every window. Passage vectors are **cached per document** (a small LRU shared by
  `/api/process` and `/api/qa-ask`), so follow-up questions only embed the question.
  (Retrieval is a no-op for short documents that split into at most 6 passages anyway.)
- Retrieved passages that are adjacent in the document are **merged into contiguous blocks
  before tokenization**. A lone passage never overflows a 384-token window, so feeding
  passages individually meant the stride did nothing. Once adjacent passages are merged,
  the block tiles into multiple windows at a 128-token stride, so an answer
  straddling a passage seam is recoverable. Retrieved passages that are *not* adjacent
  stay separate single-window blocks — there is no seam between them to straddle.
- Candidate spans are restricted to *context* tokens, must satisfy `end >= start`, and are
  capped at 40 tokens.
- SQuAD2 models emit a no-answer score at the `[CLS]` position. A span is only returned if
  it outscores that null; otherwise the answer is empty. Confidence is the sigmoid of that
  margin.
- Answers are sliced from the original text by character offset, so casing and punctuation
  are preserved and the frontend can highlight the exact source region. Offsets are
  relative to the text as sent, including any leading whitespace.

### How summarization works

DistilBART accepts 1024 tokens (roughly 750 words) and silently truncates anything longer,
so every input it sees is sized to fit. Documents up to 400 words are summarized in one
pass. Longer documents are split into evenly-sized, sentence-aligned chunks of ~512
tokens (sentences with no punctuation, common in PDF extraction, are broken into word
windows). Every sentence goes into exactly one chunk, so the whole document is covered.
Each chunk is summarized, near-duplicate sentences are dropped, and the partials are
condensed into the executive summary — recursively, if the partials themselves exceed
1024 tokens. There is no cap on the number of chunks, so summarization time grows
linearly with document length (a 6,000-word document takes ~50 s on a CPU laptop).

---

## Performance

All five model loaders (in `backend/cadis/models/registry.py`) are wrapped in
`@lru_cache(maxsize=1)`, so weights load once per worker process and are reused.
`backend/scripts/benchmark.py` measures what that buys:

```
python backend/scripts/benchmark.py
```

One run on a CPU-only Windows laptop with weights already in `~/.cache/huggingface`
(`python benchmark.py 100 400`, measured before the Phase 0 refactor):

| Document | Warm request (inference) | Cold request (load + inference) | Ratio |
|---|---|---|---|
| 100 words | 3.3 s | 38.8 s | **11.8×** |
| 400 words | 11.3 s | 46.8 s | **4.2×** |

Absolute numbers vary a lot between machines and runs (the figures previously quoted
here were 7.9 s / 16.8 s warm with ~23 s load), so treat them as illustrative. Two things to
know about the method:

- The *cold* column is computed, not measured: it is the one-time load cost plus the warm
  inference time. That load cost (35.5 s in the run above) includes importing
  torch/transformers as well as loading weights from disk.
- Load is paid exactly once per worker; afterwards all five `lru_cache` lookups together
  take tens of microseconds.

What holds across runs is the shape: the cold/warm ratio is **highest on short documents**,
where load dominates, and falls as inference grows — it is a property of the document,
not a single headline number.

A true cold start *in deployment* is larger than any of these, because the Dockerfile
deliberately does not pre-download weights (it blew past the HF Spaces build timeout), so
the first request after a container wake also pays a ~2.1 GB network download. That cost
is bandwidth-dependent and not reproducible as a fixed figure, which is why it is not
quoted here.

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20.9+ (required by Next.js 16)

### 1. ML Backend

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn cadis.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

(`uvicorn api_server:app` from the repository root still works; `api_server.py` is a
compatibility shim during the V2 migration.)

Models download from HuggingFace on first use (~2.1 GB total, most of it DistilBART) and are cached afterwards.

### 2. Frontend

```bash
cd client
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 3. Tests and evaluation

```bash
pip install -r requirements-dev.txt            # pytest + httpx, on top of requirements.txt
pytest backend                                 # unit tests with fake models (seconds)
pytest backend -m slow                         # real models (downloads ~2 GB on first run)
python backend/scripts/eval.py                 # retrieval + answer quality on data/eval
python backend/scripts/eval.py --save phaseN   # also write data/eval/results/phaseN.json
```

CI (`.github/workflows/ci.yml`) runs the unit tests, `npx tsc --noEmit` and
`npm run build` on every push to `main`.

### Environment Variables

Backend settings live in `backend/cadis/config.py` and are read from environment
variables with a `CADIS_` prefix (a `.env` file works in development). The V1 names in
brackets are still accepted.

| Variable | Service | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | Frontend | FastAPI base URL (default `http://localhost:8000`) |
| `CADIS_FRONTEND_URLS` (`FRONTEND_URL`) | Backend | Comma-separated frontend origins added to the CORS allow-list |
| `CADIS_QA_MODEL` (`QA_MODEL`) | Backend | QA model (default `deepset/roberta-base-squad2`) |
| `CADIS_SUM_MODEL` (`SUM_MODEL`) | Backend | Summarization model |
| `CADIS_NER_MODEL` (`NER_MODEL`) | Backend | NER model |
| `CADIS_EMB_MODEL` (`EMB_MODEL`) | Backend | Embedding model |

Tuning values (passage size, QA window, NER window, summary chunk size, …) are listed in
`config.py`, each overridable the same way.

---

## API

| Endpoint | Method | Body | Returns |
|----------|--------|------|---------|
| `/health` | GET | — | Service status |
| `/api/extract` | POST | `multipart/form-data` file | `{ text, chars, words }` |
| `/api/process` | POST | `{ text }` | All six module results |
| `/api/qa-ask` | POST | `{ text, question }` | `{ question, answer, confidence, start, end }` |

---

## Project Structure

```
CADIS/
├── backend/
│   ├── cadis/              # FastAPI backend package
│   │   ├── main.py         # app factory: routers + CORS
│   │   ├── config.py       # all settings (pydantic-settings)
│   │   ├── api/            # health + V1 endpoints (legacy.py)
│   │   ├── analysis/       # the six modules: preprocessing, embeddings view, NER, ambiguity, summary
│   │   ├── answer/         # extractive QA (RoBERTa span decoding, passage cache)
│   │   ├── ingest/         # file parsers (PDF / DOCX / TXT)
│   │   └── models/         # registry.py — the only place models are loaded
│   ├── tests/              # unit/ (fake models) and slow/ (real models)
│   ├── scripts/            # benchmark.py, eval.py
│   └── pyproject.toml      # pytest configuration
├── api_server.py           # compatibility shim: from cadis.main import app
├── Dockerfile              # HuggingFace Spaces image (CPU torch; models fetched on first use)
├── requirements.txt        # Python dependencies (requirements-dev.txt adds test tools)
├── hf_README.md            # HF Space card metadata
├── .github/workflows/      # CI
├── client/                 # Next.js 16 frontend
│   ├── app/
│   │   ├── page.tsx        # Landing page
│   │   ├── launch/         # Upload / paste / sample + pipeline runner
│   │   └── pipeline/       # One page per module
│   ├── components/         # Landing sections + shadcn/ui primitives
│   └── lib/utils.ts        # Tailwind className helper (cn)
└── data/
    ├── ambiguity_dataset.csv
    └── eval/               # evaluation documents, questions and saved results
```

---

## License

This project is for academic and research purposes.
