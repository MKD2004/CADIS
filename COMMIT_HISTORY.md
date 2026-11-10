# CADIS — Commit History

Every commit on `main`, oldest first, with what it touched and notes that help when
debugging. Use it to answer *"when did this break, and what changed?"*.

Related: [`DECISIONS.md`](DECISIONS.md) (why) · [`ARCHITECTURE_V2.md`](ARCHITECTURE_V2.md)
(how it fits together).

---

## How to use this when something breaks

| Goal | Command |
|---|---|
| See exactly what a commit changed | `git show <hash>` · files only: `git show --stat <hash>` |
| Find which commit last changed a line | `git blame <file>` · then `git show <hash>` |
| Find every commit that touched a file | `git log --oneline -- <file>` |
| Find the commit that introduced a bug | `git bisect start` · `git bisect bad` · `git bisect good <hash>` · test · repeat · `git bisect reset` |
| Undo a commit safely (keeps history) | `git revert <hash>` |
| Run the app as it was at a commit | `git switch --detach <hash>` · back: `git switch main` |

Good "known working" points for `git bisect good`:

| Hash | State |
|---|---|
| `fab64bf` | V1 backend after the QA sliding-window fix (deployed on HF Spaces at the time) |
| `5a7ef48` | V1 after the Nov 2026 audit: README corrected, summary + highlight fixes, npm audit clean, Docker image built and smoke-tested (15/15 checks) |

## How to keep this file up to date

- **Add one row per commit**, at the bottom of the newest section, in this format:
  `| hash | date | type | message | area | notes |`.
- A commit cannot contain its own hash, so **each commit adds the row for the commit
  before it** (or a `docs: update commit history` commit adds the missing rows).
  The newest commit may therefore be missing here — check with `git log -3 --oneline`.
- **Notes column:** write what a future debugger needs — what behaviour changed, known
  side effects, the ADR it relates to, or "safe to ignore" for trivial commits.
- Start a new section when a new phase of `CADIS V2.md` begins.
- Regenerate the raw list at any time with:
  `git log --reverse --format='| %h | %ad | %s |' --date=short`

**Type** = Conventional Commit type (`feat`, `fix`, `docs`, `chore`, `refactor`, `test`,
`ci`), or `—` for older commits that did not use the convention, or `merge`.

---

## Era 1 — Streamlit prototype (2026-03-30 → 2026-04-19)

A Streamlit app (`app.py`) with one Python file per NLP module in `modules/`.
**All of this code was deleted later** (`436170a`, `7fa107a`).

| Hash | Date | Type | Message | Area | Notes |
|---|---|---|---|---|---|
| `0f04d7c` | 2026-03-30 | — | Initial commit: Core CADIS Streamlit pipeline and NLP modules | `app.py`, `modules/` | Origin of the six modules (preprocessing, embeddings, NER/IE, ambiguity, QA, summarizer). |
| `6cf3f3a` | 2026-04-11 | feat | add ambiguity evaluation script and finalize paper metrics | `modules/`, eval scripts, `data/` | Adds `data/ambiguity_dataset.csv` (still in repo) and evaluation scripts (later deleted). |
| `adde1d1` | 2026-04-14 | — | Enhanced UI modification | `app.py`, `ui_components.py`, `modules/` | Large Streamlit UI rewrite. |
| `87395e8` | 2026-04-14 | — | Update requirements.txt to include new packages | `requirements.txt` | |
| `8bfbc9c` | 2026-04-14 | — | Create README.md for CADIS project | `README.md` | |
| `b665fec` | 2026-04-15 | — | Simplified into module wise file structure | `app.py`, `modules/` | |
| `57f7d8e` | 2026-04-15 | merge | Module wise file structure | — | **Only merge commit** in history (parents `b665fec`, `8bfbc9c`). |
| `620d03d` | 2026-04-19 | feat(ml) | integrate DistilBART summarizer and RoBERTa QA extraction | `ml-service/` | Creates the FastAPI `ml-service/` (ChromaDB, routers, services). ⚠ Also committed `chroma_store/` data and a font file — removed in `4431886`. |
| `44cb38d` | 2026-04-19 | fix(gateway) | resolve RAG payload routing and data caching | `server/` | Creates the Node/Express gateway. ⚠ Committed **903 `node_modules` files** — removed in `4431886`; history still contains them. |
| `d5cb221` | 2026-04-19 | fix(ui) | resolve summary rendering and ambiguity metrics | `client/` (Vite + React) | Creates the first Vite/React client. |
| `7b85478` | 2026-04-19 | — | Revise README for improved clarity and organization | `README.md` | |
| `11183cb` | 2026-04-19 | — | Update requirements.txt with new and upgraded packages | `requirements.txt` | |

## Era 2 — Three-service build: Vite client + Node gateway + ML service (2026-06-25)

| Hash | Date | Type | Message | Area | Notes |
|---|---|---|---|---|---|
| `fb30cee` | 2026-06-25 | chore | update project config, dependencies, and gitignore | `client/` config | |
| `a9a2ac8` | 2026-06-25 | feat(ui) | implement dark theme design system | `client/src` | |
| `c52f166` | 2026-06-25 | feat(ui) | add ReactBits animation components | `client/src` | |
| `8cfadb8` | 2026-06-25 | feat(ui) | add layout and navigation components | `client/src` | |
| `94a627b` | 2026-06-25 | feat(ui) | add app shell, routing, home page, and document context | `client/src` | |
| `dc17d3c` | 2026-06-25 | feat(frontend) | wire upload flow to backend pipeline | `client/src` | |
| `548a8b1` | 2026-06-25 | feat(frontend) | connect all 6 module pages to live document data | `client/src` | |
| `09898d8` | 2026-06-25 | feat(ml) | integrate DistilBART summarizer, RoBERTa QA, and sample seeding | `ml-service/` | ml-service used `unstructured[pdf]`, GLiNER and ChromaDB (see DECISIONS ADR-007, ADR-016). |
| `7bab290` | 2026-06-25 | feat(gateway) | add pipeline orchestration, RAG chat, and rate limiting | `server/` | Gateway rate limiter + validation middleware (gateway later removed, ADR-001). |
| `219ea2e` | 2026-06-25 | chore | add unused component scaffolds for future use | `client/src` | |
| `bafd6b5` | 2026-06-25 | docs | add comprehensive project briefing | `project_briefing.md` | Deleted in `436170a`. |
| `0ea05a8` | 2026-06-25 | docs | update README with full project documentation | `README.md` | |
| `1752eb0` | 2026-06-25 | refactor | update CADIS evaluator with improved metrics | `cadis_evaluator.py` | Deleted later. |
| `4431886` | 2026-06-25 | chore | remove chroma_store and node_modules from tracking | `server/node_modules`, `ml-service/chroma_store` | Cleanup of the ⚠ commits above. The files remain in git history (repo size). |

## Era 3 — Next.js frontend + single-file FastAPI backend (2026-06-30)

The architecture V1 is based on. Frontend rebuilt in Next.js; backend became
`api_server.py`; deployed to Vercel + HF Spaces.

| Hash | Date | Type | Message | Area | Notes |
|---|---|---|---|---|---|
| `67517eb` | 2026-06-30 | chore | remove old Vite/React frontend | `client/` | |
| `2aba8b2` | 2026-06-30 | chore | add Next.js project configuration | `client/` config | `next.config.mjs` sets `ignoreBuildErrors: true` — builds do not type-check (ADR-004). |
| `d2dc266` | 2026-06-30 | feat | add global styles and CSS animations | `client/styles` | |
| `8ae045e` | 2026-06-30 | feat | add utility libraries and NLP helpers | `client/lib` | Added `lib/nlp-utils.ts` (deleted in `7fa107a`). |
| `22d4039` | 2026-06-30 | feat | add custom React hooks | `client/hooks` | |
| `9911c9a` | 2026-06-30 | feat | add public assets and icons | `client/public` | |
| `d94839c` | 2026-06-30 | feat | add shadcn/ui component library | `client/components/ui` | |
| `87c8284` | 2026-06-30 | feat | add Navbar component with CADIS branding and launch CTA | `client/components` | |
| `2bfb83e` | 2026-06-30 | feat | add Hero section with animated headline and pipeline stats | `client/components` | |
| `0ffdfdd` | 2026-06-30 | feat | add ML model marquee banner | `client/components` | |
| `81eae76` | 2026-06-30 | feat | add Bento grid showcasing 6 NLP modules with live animations | `client/components` | |
| `1214510` | 2026-06-30 | feat | add Pipeline walkthrough section with 6 numbered module cards | `client/components` | |
| `ff0164e` | 2026-06-30 | feat | add final CTA section with GitHub link | `client/components` | |
| `91cecdf` | 2026-06-30 | feat | add Footer with GitHub links and pipeline column nav | `client/components` | |
| `6b96b1e` | 2026-06-30 | feat | add PipelineNav component with step progress indicator | `client/components` | |
| `45fe8be` | 2026-06-30 | feat | add SmoothScroll wrapper component | `client/components` | |
| `385f3a6` | 2026-06-30 | feat | add ThemeProvider component | `client/components` | |
| `fb182c6` | 2026-06-30 | feat | add Next.js app layout and landing page | `client/app` | |
| `ba3ecc5` | 2026-06-30 | feat | add launch page with document upload, paste, and sample documents | `client/app/launch` | Stores the result in `localStorage` (size limit issue — ADR-004). |
| `848b799` | 2026-06-30 | feat | add pipeline layout wrapper | `client/app/pipeline` | |
| `a402b95` | 2026-06-30 | feat | add Preprocessing pipeline page with spaCy token/POS display | `client/app/pipeline` | |
| `40fb868` | 2026-06-30 | feat | add Embeddings pipeline page with vector scatter and similarity matrix | `client/app/pipeline` | Scatter uses raw dims 0/1, not a projection (fix planned, Phase 0). |
| `2d2d4f0` | 2026-06-30 | feat | add NER pipeline page with BERT entity confidence bars and SVO relations | `client/app/pipeline` | |
| `ed0d160` | 2026-06-30 | feat | add Ambiguity Resolution pipeline page with PP attachment and anaphora detection | `client/app/pipeline` | |
| `28441c5` | 2026-06-30 | feat | add QA Engine pipeline page with custom question input and span highlighting | `client/app/pipeline` | |
| `d7ab0dc` | 2026-06-30 | feat | add Summarization pipeline page with DistilBART executive summary and timeline | `client/app/pipeline` | |
| `8357e15` | 2026-06-30 | feat | add FastAPI backend with 6-module NLP pipeline endpoint | `api_server.py` | **Birth of V1 backend.** |
| `3846bd7` | 2026-06-30 | chore | add pnpm lockfile | `client/pnpm-lock.yaml` | Deleted in `76c0e6c` (stale, vulnerable pins). |
| `b0cabd0` | 2026-06-30 | feat | add app-level global CSS entry point | `client/app` | |
| `436170a` | 2026-06-30 | chore | remove old Streamlit app, evaluation scripts, and dataset files | root | |
| `8d285cf` | 2026-06-30 | chore | update requirements.txt with current package versions | `requirements.txt` | |
| `33e50e7` | 2026-06-30 | feat | add Dockerfile for Hugging Face Spaces deployment | `Dockerfile`, `hf_README.md` | |
| `8ac9bac` | 2026-06-30 | fix | allow Vercel frontend origin via FRONTEND_URL env var | `api_server.py` | CORS allow-list + `FRONTEND_URL`. If the deployed frontend gets CORS errors, check this env var on the Space. |
| `801f44f` | 2026-06-30 | feat | use NEXT_PUBLIC_API_URL env var for backend API calls | `client/app` | |
| `866857b` | 2026-06-30 | fix | correct template literal syntax for API URL env var | `client/app` | Fix for `801f44f`. |
| `0daed02` | 2026-06-30 | ci | trigger Vercel redeploy with Next.js framework preset | — | **Empty commit** (no file changes). |
| `65abe62` | 2026-06-30 | ci | add vercel.json with explicit Next.js framework config | `client/vercel.json` | |
| `f32f6fe` | 2026-06-30 | ci | explicitly set Next.js build commands in vercel.json | `client/vercel.json` | |
| `30983f7` | 2026-06-30 | fix | replace question-answering pipeline with direct model call for transformers v5 | `api_server.py` | transformers v5 broke the QA `pipeline`. If QA breaks after a library upgrade, start here. |

## Era 4 — Correctness fixes (2026-07-20 → 2026-10-24)

| Hash | Date | Type | Message | Area | Notes |
|---|---|---|---|---|---|
| `7fa107a` | 2026-07-20 | fix | correct QA span decoding and summarize whole documents | `api_server.py`, client, deletes `ml-service/`, `server/`, `modules/` | QA: context-only spans, `end >= start`, 40-token cap, null-score check, char-offset slicing, passages + MiniLM retrieval, roberta-base-squad2. Summary: map-reduce. Removed 3 unused backends (ADR-001). Big commit — use `git show --stat`. |
| `74eebda` | 2026-07-20 | — | Delete context.md | `context.md` | |
| `ee58e66` | 2026-07-20 | fix | align Dockerfile and requirements with what actually builds on HF Spaces | `Dockerfile`, `requirements.txt` | CPU torch first; no model pre-download (build timeout). If the Space build fails, compare with this commit (ADR-005). |
| `d91a285` | 2026-07-20 | chore | keep context.md as a local-only reference file | `.gitignore` | `context.md` is git-ignored. |
| `fab64bf` | 2026-10-24 | fix | make the QA sliding window actually fire, and measure the cache claim | `api_server.py`, `benchmark.py`, `README.md` | Merges adjacent retrieved passages before windowing so the 384/128 stride works; embeds passages once per request; adds `benchmark.py`. ✅ known-good point. |

## Era 5 — Audit, cleanup and V2 planning (2026-11-09)

| Hash | Date | Type | Message | Area | Notes |
|---|---|---|---|---|---|
| `adf0eeb` | 2026-11-09 | fix | summarize the whole document and align QA highlight offsets | `api_server.py`, `client/app/launch`, `client/app/pipeline/qa` | Summary: token-sized chunks (~512), **no chunk cap** (latency grows with length), recursive reduce. QA offsets relative to text as sent; frontend stores trimmed text. If summaries get slow on long docs, this is why. |
| `094f86f` | 2026-11-09 | docs | correct README claims against the code | `README.md`, `benchmark.py` | Next 16 / Node 20.9+, ~2.1 GB models, measured benchmark numbers. |
| `9d4a164` | 2026-11-09 | chore(client) | clear npm audit findings | `client/package*.json` | Next 16.0.10 → **16.4.5**; removed unused zod, @hookform/resolvers, @nuxt/kit. If a frontend page breaks, check Next.js 16.1–16.4 changes first. Build + tsc + route checks passed. |
| `76c0e6c` | 2026-11-09 | chore(client) | remove stale pnpm-lock.yaml | `client/pnpm-lock.yaml` | npm only (ADR-026). |
| `5a7ef48` | 2026-11-09 | chore | drop unused pandas, requests and httpx from requirements | `requirements.txt` | requests/httpx still installed transitively (spaCy, huggingface_hub). Docker image built and smoke-tested after this. ✅ known-good point. |
| `de42622` | 2026-11-09 | docs | add CADIS V2 roadmap for large and multi-document RAG | `CADIS V2.md` | Phase plan 0–6. |

## V2 — Phase 0: Foundation

*Rows are added here as V2 work is committed. The commit adding `ARCHITECTURE_V2.md`,
`DECISIONS.md` and this file is recorded by the next commit.*

| Hash | Date | Type | Message | Area | Notes |
|---|---|---|---|---|---|
