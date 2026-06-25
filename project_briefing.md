# CADIS — Context-Aware Document Intelligence System

## Project Briefing

**Author:** Mahith K (MKD2004)
**Stack:** React 18 + Vite | Node.js Express Gateway | FastAPI + Python ML Services
**Repo:** github.com/MKD2004/CADIS

---

## 1. What is CADIS?

CADIS is a **fully local, privacy-first document intelligence platform** that processes PDF documents through **6 sequential neural modules** — from raw text extraction to executive summarization — entirely on the user's machine. No data ever leaves the local environment.

The system combines:
- **4 ML models** running simultaneously (GliNER, MiniLM, RoBERTa, DistilBART)
- **ChromaDB** vector database for semantic search/RAG
- A **React frontend** with animated dark-themed UI
- A **3-tier architecture**: React → Node.js Gateway → FastAPI ML Service

---

## 2. Architecture Overview

```
┌─────────────────────┐
│   React Frontend    │  Port 3000 (Vite dev server)
│   (client/)         │
└────────┬────────────┘
         │ HTTP (Vite proxy /api → :5000)
         ▼
┌─────────────────────┐
│  Node.js Gateway    │  Port 5000
│  (server/)          │  Orchestrates ML pipeline, rate limiting, validation
└────────┬────────────┘
         │ HTTP
         ▼
┌─────────────────────┐
│  FastAPI ML Service  │  Port 8000
│  (ml-service/)       │  4 ML models + ChromaDB
└──────────────────────┘
```

### Why a Gateway?

The Node.js gateway exists to **orchestrate the multi-step pipeline**. When a PDF is uploaded, the gateway:
1. Forwards the PDF to FastAPI for parsing + embedding (Step 1)
2. Calls GliNER NER endpoint (Step 2)
3. Calls DistilBART summary endpoint (Step 3)
4. Runs ambiguity keyword detection (Step 4)
5. Assembles the final payload and returns it to React

This keeps the FastAPI service focused on single-purpose ML endpoints while the gateway handles orchestration.

---

## 3. The 6 Neural Modules (Pipeline)

When a document enters CADIS, it flows through these stages:

| Module | Name | What It Does | Model/Tech |
|--------|------|-------------|------------|
| MOD-01 | **NLP Preprocessing** | Tokenization, sentence splitting, word classification | Text processing (word-based) |
| MOD-02 | **Semantic Embeddings** | Converts text chunks into 384-dim dense vectors, stores in ChromaDB | `all-MiniLM-L6-v2` (sentence-transformers) |
| MOD-03 | **NER + IE** | Zero-shot named entity recognition with arbitrary labels | `GliNER` (urchade/gliner_base) |
| MOD-04 | **Ambiguity Detection** | Scans for ambiguous language patterns (keyword-based) | Regex/keyword matching |
| MOD-05 | **QA Engine** | Interactive question answering via semantic retrieval + extraction | `MiniLM` retrieval → `RoBERTa` QA extraction |
| MOD-06 | **Summary Generator** | Abstractive executive summary generation | `DistilBART` (sshleifer/distilbart-cnn-12-6) |

### Pipeline Data Flow

```
PDF Upload
    │
    ▼
[unstructured.io] → Parse PDF into text blocks + images
    │
    ▼
[MiniLM] → Chunk text (400 words) → Embed → Store in ChromaDB
    │
    ▼
[GliNER] → Extract entities (zero-shot, any labels)
    │
    ▼
[Ambiguity Scanner] → Keyword detection for unclear language
    │
    ▼
[DistilBART] → Generate abstractive summary
    │
    ▼
[RoBERTa QA] → Available for interactive Q&A via ChromaDB retrieval
    │
    ▼
Assembled JSON payload → React Dashboard
```

---

## 4. ML Models — Deep Dive

### 4.1 all-MiniLM-L6-v2 (Embeddings)
- **Purpose:** Converts text chunks into 384-dimensional dense vectors
- **Architecture:** 6-layer BERT variant, distilled from MiniLM
- **Used by:** ChromaDB for semantic similarity search
- **How it works:** Each text chunk is encoded into a fixed-size vector. At query time, the user's question is also encoded, and cosine similarity finds the most relevant chunks.
- **Why this model:** Tiny (80MB), fast inference, excellent quality for semantic search

### 4.2 GliNER (Named Entity Recognition)
- **Purpose:** Zero-shot NER — extract entities with *any* labels, no fine-tuning needed
- **Model ID:** `urchade/gliner_base`
- **Key advantage:** You pass labels like `["Threat Actor", "Malware", "CVE"]` at inference time and it extracts matching spans. Traditional NER models (spaCy, BERT-NER) need retraining for new entity types.
- **Domain presets:** Cybersecurity, Legal, Finance, Medical, General
- **Output:** Array of `{text, label, score, start, end}` spans

### 4.3 RoBERTa QA (Question Answering)
- **Purpose:** Extractive QA — given a question and a context paragraph, extract the exact answer span
- **Model ID:** `deepset/roberta-base-squad2`
- **How it works with RAG:**
  1. User asks a question
  2. MiniLM embeds the question → ChromaDB returns top-3 relevant chunks
  3. Chunks are concatenated as context
  4. RoBERTa extracts the exact answer span from that context
- **Key:** This is *extractive* — it highlights text that already exists in the document, never hallucinating

### 4.4 DistilBART (Summarization)
- **Purpose:** Abstractive summarization — condenses long documents into concise summaries
- **Model ID:** `sshleifer/distilbart-cnn-12-6`
- **Architecture:** 12-layer encoder, 6-layer decoder (distilled from BART-Large-CNN)
- **Input limit:** ~50,000 characters (handled by truncation)
- **Output:** Executive summary paragraph

---

## 5. File-by-File Reference

### 5.1 FastAPI ML Service (`ml-service/`)

| File | Purpose |
|------|---------|
| `main.py` | App entry point. Lifespan manager loads all 4 models at startup. Creates FastAPI app with CORS, routers, health endpoints. Run with `uvicorn main:app --port 8000` |
| `core/config.py` | Pydantic-settings based config. Model IDs, ChromaDB paths, upload limits. Override via env vars or `.env` |
| `core/logging.py` | Structured logging setup |
| `core/metrics.py` | Request counter and latency tracking |
| `models/schemas.py` | All Pydantic v2 request/response schemas: `ParsedDocument`, `NERRequest`, `NERResponse`, `SearchRequest`, `SearchResponse`, `SummaryRequest`, etc. |
| `routers/document.py` | `POST /api/v1/process-pdf` — Parses PDF with unstructured.io, optionally runs VLM on images, chunks text, upserts into ChromaDB |
| `routers/ner.py` | `POST /api/v1/ner/extract` — Zero-shot NER with GliNER. Also serves label presets (`/label-presets`) |
| `routers/search.py` | `POST /api/v1/search/query` — Semantic search (MiniLM) + QA extraction (RoBERTa). Also: `/upsert`, `/stats`, `/samples` |
| `routers/summary.py` | `POST /api/v1/summary/generate` — DistilBART abstractive summarization |
| `services/vector_store.py` | Singleton ChromaDB service. MiniLM embedding function adapter. Handles: `upsert_document`, `semantic_search`, `collection_stats`, `delete_document`. Persistent storage at `./chroma_store` |
| `services/gliner_ie.py` | Singleton GliNER service. Thread-safe lazy loading. Methods: `extract(text, labels, threshold)`, `extract_batch()` |
| `services/qa.py` | Singleton RoBERTa QA service. Uses HuggingFace `pipeline("question-answering")`. Method: `answer_question(question, context)` |
| `services/summarizer.py` | Singleton DistilBART service. Method: `summarize(text)` → `{text, inference_ms}` |
| `services/multimodal.py` | VLM service for image descriptions (Qwen-VL). Currently disabled (`vlm_enabled=False`) |
| `scripts/seed_documents.py` | Seeds 3 sample documents (cybersec, legal, medical) into ChromaDB at startup |

### 5.2 Node.js Gateway (`server/`)

| File | Purpose |
|------|---------|
| `server.js` | Express app. Routes: `GET /health`, `GET /api/samples`, `POST /api/process-pdf` (orchestrator), `POST /api/sample-analyze/:docId`, `POST /api/chat` (RAG Q&A). Proxies to FastAPI at `http://127.0.0.1:8000` |
| `middleware/rateLimiter.js` | Rate limiting: `strictLimiter` (5 req/min for heavy endpoints), `uploadLimiter` (3 req/min for PDF upload), `generalLimiter` |
| `middleware/validate.js` | Input validation: `validatePdfUpload` (checks file exists, is PDF, size < 50MB), `validateChatQuery` (checks query string) |

### 5.3 React Frontend (`client/src/`)

#### Core Files

| File | Purpose |
|------|---------|
| `main.jsx` | Entry point. Wraps app in `BrowserRouter` + `DocumentProvider` |
| `App.jsx` | Root shell. Renders: `TargetCursor`, `DarkVeil` (WebGL background), `Navbar`, `StaggeredMenu`, `<Routes>`. 9 routes: `/`, `/analyze`, `/module-1` through `/module-6` |
| `index.css` | Complete dark design system. CSS custom properties (tokens): `--background: #000`, `--primary: #298DFF`, `--card: #0d0d14`, etc. Google Fonts (Inter, JetBrains Mono, Play). Component classes: `surface-card`, `glass-card`, `ink-card` |
| `context/DocumentContext.jsx` | React context holding the analyzed document data. `useDocument()` hook returns `{doc, setDoc, clearDoc}`. Shared across all module pages. |
| `lib/api.js` | Centralized API client: `checkHealth()`, `fetchSamples()`, `processPdf(file)`, `analyzeSample(docId)`, `chat(query, documentId)` |
| `lib/utils.js` | `cn()` utility (clsx + tailwind-merge) |

#### Pages

| File | Purpose |
|------|---------|
| `pages/Home.jsx` | Landing page. Giant "CADIS" title (Play font), TextType typing effects on section headings, CountUp stats, "Upload Document" button → `/analyze` |
| `pages/Analyze.jsx` | Upload orchestrator. Shows `HeroUpload` (dropzone) → on upload calls `processPdf()` → stores result in `DocumentContext` → shows `ResultsDashboard` |
| `pages/Module1.jsx` | **Preprocessing.** Reads from `DocumentContext`. Shows token count, sentence count, unique lemmas, token stream preview (content vs stop words), first 5 sentences |
| `pages/Module2.jsx` | **Embeddings.** Shows chunks stored, embedding dims (384), model name. Embedded sentences preview. **Working semantic search** — queries the actual document via `/api/chat` |
| `pages/Module3.jsx` | **NER + IE.** Shows real entities from GliNER grouped by category with confidence scores. Annotated text with inline entity highlights. Raw JSON viewer |
| `pages/Module4.jsx` | **Ambiguity.** Shows ambiguity count from pipeline. Highlights ambiguous keywords found in context. Reference cards for ambiguity types (PP-attachment, anaphoric, lexical, semantic) |
| `pages/Module5.jsx` | **QA Engine.** Fully interactive — type a question, get a real answer from RoBERTa. Suggested questions, latency metrics (MiniLM + RoBERTa), source context preview |
| `pages/Module6.jsx` | **Summary.** Shows DistilBART executive summary, key sentences extracted from it, compression ratio, word counts. Side-by-side original vs summary comparison |

#### Animation Components (from ReactBits)

| File | Purpose |
|------|---------|
| `DarkVeil.jsx/css` | WebGL animated background using `ogl` library. CPPN neural network shader. `hueShift={350}` for blue |
| `TargetCursor.jsx/css` | Custom crosshair cursor, only visible on `.cursor-target` elements. `cursorColor="#fff"`, blue on target |
| `StaggeredMenu.jsx/css` | Slide-out navigation panel (left side). GSAP-powered stagger animation. Lists all routes (Home, Analyze, 6 modules) |
| `PillNav.jsx/css` | Animated pill-style tab navigation in the Navbar. GSAP circle-fill hover effect |
| `BorderGlow.jsx/css` | Pointer-tracking edge glow card wrapper. Applied to all cards across all module pages |
| `CountUp.jsx` | Scroll-triggered animated number counter (motion library) |
| `TextType.jsx/css` | Typewriter text effect with variable speed. Used on Home page section headings |
| `DecryptedText.jsx` | Scramble-reveal text effect. Used on module page titles via `ModuleHeader` |
| `GradientText.jsx/css` | Animated gradient text (motion library). Was used on CADIS title, now removed |

#### UI Components

| File | Purpose |
|------|---------|
| `Navbar.jsx` | Fixed top bar. CADIS logo, PillNav (Home + Analyze tabs), search bar (filters/navigates to routes), health indicator (polls `/health` every 30s with model status tooltip), GitHub link |
| `HeroUpload.jsx` | PDF dropzone with drag states. Fetches sample documents from `/api/samples`. Shows file name/size after selection. Processing spinner state |
| `ResultsDashboard.jsx` | Bento grid dashboard after analysis. Cards: Executive Summary, Extracted Entities (filterable by label), Document Metadata (pages, chunks, ambiguities, pipeline flags), Raw JSON viewer, Interactive Q&A chat |
| `ModuleHeader.jsx` | Shared header for module pages. Module code, title (with DecryptedText effect), subtitle |
| `ModuleNav.jsx` | Previous/Next navigation between modules |
| `NoDocument.jsx` | Empty state shown on module pages when no document is uploaded. Links to `/analyze` |
| `CompletionStrip.jsx` | Green completion banner at bottom of each module page |
| `PageFooter.jsx` | Page footer |
| `ErrorBoundary.jsx` | React error boundary. `PanelErrorBoundary` for individual dashboard cards |

#### Unused/Legacy Components (still in codebase)

| File | Status |
|------|--------|
| `AppSidebar.jsx` | Replaced by StaggeredMenu |
| `Counter.jsx/css` | Replaced by CountUp |
| `GradualBlur.jsx/css` | Added then removed (user didn't like it) |
| `LightRays.jsx/css` | Replaced by DarkVeil (invisible on dark theme) |
| `StartupLoader.jsx` | Not currently used |
| `PipelineProgress.jsx` | Not currently used |
| `ProcessingTerminal.jsx` | Not currently used |

---

## 6. API Endpoints Reference

### Gateway (Port 5000)

| Method | Path | Purpose | Calls |
|--------|------|---------|-------|
| GET | `/health` | Full health check (gateway + ML models + ChromaDB) | FastAPI `/health` |
| GET | `/api/status` | Gateway status | — |
| GET | `/api/samples` | List pre-loaded sample documents | FastAPI `/api/v1/search/samples` |
| POST | `/api/process-pdf` | **Main pipeline.** Upload PDF → parse → embed → NER → summarize → ambiguity | FastAPI: `/process-pdf` → `/ner/extract` → `/summary/generate` |
| POST | `/api/sample-analyze/:docId` | Analyze a pre-loaded sample document | FastAPI: `/search/query` → `/ner/extract` → `/summary/generate` |
| POST | `/api/chat` | RAG Q&A. Sends query + optional document_id filter | FastAPI `/api/v1/search/query` |

### FastAPI ML Service (Port 8000)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/process-pdf` | Parse PDF (unstructured.io), chunk, embed, store in ChromaDB |
| POST | `/api/v1/ner/extract` | Zero-shot NER with GliNER |
| POST | `/api/v1/ner/extract-batch` | Batch NER across multiple texts |
| GET | `/api/v1/ner/label-presets` | Domain label presets (cybersecurity, legal, finance, medical, general) |
| POST | `/api/v1/search/query` | Semantic search (MiniLM) + QA extraction (RoBERTa) |
| POST | `/api/v1/search/upsert` | Manually store text chunks |
| GET | `/api/v1/search/stats` | ChromaDB collection statistics |
| GET | `/api/v1/search/samples` | List pre-loaded sample documents |
| POST | `/api/v1/summary/generate` | DistilBART abstractive summarization |
| GET | `/health` | Model readiness check |
| GET | `/metrics` | Inference latency metrics |

---

## 7. Key Design Decisions (Interview Prep)

### Why Local-Only?
Privacy. CADIS processes sensitive documents (legal, medical, cybersecurity). Zero data leaves the machine. No cloud API calls. All 4 models run on CPU (no GPU required, though GPU accelerates inference).

### Why GliNER Instead of spaCy NER?
Traditional NER (spaCy, BERT-NER) requires training on labeled data for each entity type. GliNER is **zero-shot** — you pass labels like `["Threat Actor", "CVE"]` at runtime and it extracts matching spans. This makes CADIS domain-agnostic without retraining.

### Why a 3-Tier Architecture?
- **FastAPI** handles ML inference (Python ecosystem: transformers, sentence-transformers, gliner)
- **Node.js Gateway** handles orchestration, rate limiting, validation (lightweight, non-blocking I/O)
- **React Frontend** handles presentation (animated, interactive UI)

Separating the gateway from the ML service means:
- The ML service stays focused on single-purpose endpoints
- Pipeline orchestration logic (4-step process for PDF) lives in the gateway
- Rate limiting and validation happen before hitting the expensive ML endpoints

### Why ChromaDB?
ChromaDB is a lightweight, persistent vector database that runs locally. It stores document embeddings on disk (survives restarts) and supports metadata filtering (`where` clauses). Perfect for a local-first system — no external database server needed.

### Why Extractive QA (RoBERTa) Instead of Generative (LLM)?
Extractive QA **cannot hallucinate**. It highlights text that literally exists in the document. For a research/intelligence tool, this is critical — every answer is traceable to an exact span. Generative models (GPT, etc.) would also require cloud API calls, breaking the local-only constraint.

### Why DistilBART for Summarization?
DistilBART is a distilled version of BART-Large-CNN — it runs efficiently on CPU while producing high-quality abstractive summaries. It's 50% faster than full BART with ~95% of the quality.

### The Singleton Pattern for ML Services
All 4 model services use the singleton pattern with thread-safe lazy loading:
```python
@classmethod
def get_instance(cls):
    if cls._instance is None:
        with cls._lock:
            if cls._instance is None:
                instance = cls()
                instance._load_model()
                cls._instance = instance
    return cls._instance
```
This ensures models are loaded **once** at startup and shared across all requests. Loading a transformer model takes seconds — you never want to do it per-request.

### The Document Context Pattern (Frontend)
React Context (`DocumentContext`) holds the analysis results globally. When a PDF is uploaded on `/analyze`, the result is stored in context and all 6 module pages read from it. This means:
- Navigate to any module → see your document's data
- No re-fetching or prop-drilling needed
- "No Document Loaded" state when context is empty

---

## 8. How to Run

### Prerequisites
- Python 3.11+ with `venv`
- Node.js 18+
- ~4GB RAM for ML models

### Start All 3 Services

```bash
# Terminal 1 — FastAPI ML Service (takes 30-90s to load models)
cd ml-service
.\venv\Scripts\activate    # Windows
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Node.js Gateway
cd server
npm install
node server.js

# Terminal 3 — React Frontend
cd client
npm install
npm run dev
```

Open `http://localhost:3000`

### Verify Health
```bash
curl http://localhost:5000/health
# Should show: status: ok, all models: true, chromadb: true
```

---

## 9. Frontend Design System

### Colors
- **Background:** `#000000` (pure black)
- **Primary:** `#298DFF` (blue)
- **Card:** `#0d0d14`
- **Border:** `#1e1e2e`
- **Accents:** `#22d3ee` (cyan), `#34d399` (emerald/success), `#fbbf24` (amber/warning), `#a78bfa` (violet), `#f472b6` (rose)

### Fonts
- **UI:** Inter (weight 500 default, 700 headings)
- **Monospace:** JetBrains Mono
- **CADIS Title:** Play

### Animation Libraries
- **GSAP:** StaggeredMenu, PillNav
- **motion (Framer Motion):** CountUp, GradientText, DecryptedText, page transitions
- **ogl:** DarkVeil WebGL background

### Z-Index Stack
- `z-50` — Navbar
- `z-45` — StaggeredMenu
- `z-10` — Main content
- `z-0` — DarkVeil background

---

## 10. Sample Documents (Pre-loaded in ChromaDB)

| ID | Title | Domain |
|----|-------|--------|
| `sample-cybersec-01` | APT29 Threat Intelligence Report | Cybersecurity |
| `sample-legal-01` | Meridian Corp Acquisition Agreement Summary | Legal |
| `sample-medical-01` | Clinical Case Study: Acute Myocardial Infarction | Medical |

These are seeded at startup via `scripts/seed_documents.py` and accessible from the upload page.

---

## 11. Known Limitations / Future Work

- **No POS tagging endpoint** — Module 1 does basic tokenization client-side; a real spaCy endpoint would give POS tags, dependencies, lemmas
- **Ambiguity detection is keyword-based** — A real implementation would use dependency parsing + coreference resolution
- **No document persistence** — Uploaded documents live only in the React context (lost on refresh). ChromaDB chunks persist.
- **Bundle size is ~650KB** — Could benefit from code-splitting with `React.lazy()`
- **VLM disabled** — Qwen-VL image description is scaffolded but disabled (needs GPU)
- **Single-user** — No auth, no multi-tenancy
