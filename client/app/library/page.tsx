"use client"

// Library (CADIS V2 Phase 1): collections, multi-file upload and per-document
// ingest status. Uploads return at once (202); progress comes from each job's
// Server-Sent Events stream, so closing the page never stops ingestion.

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import {
  AlertCircle, ChevronDown, ChevronRight, FileText, FolderPlus, Folder, Layers,
  Loader2, RefreshCw, RotateCcw, Trash2, Upload,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  api, ApiError, isActive, type Collection, type DocumentInfo, type Job, type Section,
} from "@/lib/api"

const ACCEPT = ".pdf,.docx,.txt"
const LAST_COLLECTION_KEY = "cadis.library.collection"

function message(err: unknown) {
  return err instanceof ApiError || err instanceof Error ? err.message : String(err)
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const STAGE_LABEL: Record<string, string> = {
  parsing: "Reading file",
  chunking: "Finding sections",
  storing: "Saving chunks",
  embedding: "Embedding",
  indexing: "Indexing",
  done: "Done",
}

function StatusBadge({ doc }: { doc: DocumentInfo }) {
  const job = doc.latest_job
  if (isActive(job)) {
    const label = job!.status === "PENDING" ? "Queued" : STAGE_LABEL[job!.stage ?? ""] ?? "Processing"
    return (
      <span className="inline-flex items-center gap-1.5 rounded-md border border-sky-800/60 bg-sky-950/50 px-2 py-0.5 text-xs text-sky-300">
        <Loader2 className="h-3 w-3 animate-spin" /> {label}
      </span>
    )
  }
  const styles: Record<string, string> = {
    READY: "border-emerald-800/60 bg-emerald-950/50 text-emerald-300",
    FAILED: "border-red-800/60 bg-red-950/50 text-red-300",
    PENDING: "border-zinc-700 bg-zinc-900 text-zinc-400",
    PROCESSING: "border-sky-800/60 bg-sky-950/50 text-sky-300",
  }
  return (
    <span className={`inline-flex rounded-md border px-2 py-0.5 text-xs ${styles[doc.status]}`}>
      {doc.status === "READY" ? "Ready" : doc.status.toLowerCase()}
    </span>
  )
}

function SectionTree({ documentId }: { documentId: string }) {
  const [sections, setSections] = useState<Section[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getSections(documentId).then(setSections).catch((e) => setError(message(e)))
  }, [documentId])

  if (error) return <p className="text-xs text-red-400">{error}</p>
  if (!sections) return <p className="text-xs text-zinc-500">Loading sections…</p>
  if (sections.length === 0) return <p className="text-xs text-zinc-500">No sections yet.</p>

  const [root, ...rest] = sections
  return (
    <div className="space-y-0.5 font-mono text-xs">
      <div className="flex justify-between text-zinc-300">
        <span className="truncate">{root.title}</span>
        {root.chunk_count > 0 && <span className="text-zinc-600">{root.chunk_count} chunks</span>}
      </div>
      {rest.length === 0 && (
        <p className="pl-4 text-zinc-600">No headings found; the document is one section.</p>
      )}
      {rest.map((s) => (
        <div key={s.id} className="flex justify-between gap-4 text-zinc-400"
             style={{ paddingLeft: `${s.level * 16}px` }}>
          <span className="truncate">{s.title}</span>
          <span className="shrink-0 text-zinc-600">
            {s.page ? `p.${s.page} · ` : ""}{s.chunk_count} chunk{s.chunk_count === 1 ? "" : "s"}
          </span>
        </div>
      ))}
    </div>
  )
}

function DocumentRow({ doc, onChanged }: { doc: DocumentInfo; onChanged: () => void }) {
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const job = doc.latest_job
  const active = isActive(job)

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    setError(null)
    try {
      await fn()
      onChanged()
    } catch (e) {
      setError(message(e))
    } finally {
      setBusy(false)
      setConfirming(false)
    }
  }

  return (
    <li className="rounded-xl border border-zinc-800 bg-zinc-900/40">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3">
        <button
          onClick={() => setOpen((o) => !o)}
          disabled={doc.current_version === 0}
          className="flex min-w-0 flex-1 items-center gap-2 text-left disabled:cursor-default"
          aria-expanded={open}
        >
          {doc.current_version > 0
            ? open ? <ChevronDown className="h-4 w-4 shrink-0 text-zinc-500" />
                   : <ChevronRight className="h-4 w-4 shrink-0 text-zinc-500" />
            : <FileText className="h-4 w-4 shrink-0 text-zinc-600" />}
          <span className="min-w-0">
            <span className="block truncate text-sm text-white">{doc.filename}</span>
            <span className="block truncate text-xs text-zinc-500">
              {[doc.title && doc.title !== doc.filename.replace(/\.[^.]+$/, "") ? doc.title : null,
                formatSize(doc.size_bytes),
                doc.pages ? `${doc.pages} pages` : null,
                doc.current_version > 1 ? `v${doc.current_version}` : null,
              ].filter(Boolean).join(" · ")}
            </span>
          </span>
        </button>

        <StatusBadge doc={doc} />

        <div className="flex items-center gap-1">
          {job?.status === "FAILED" && (
            <Button variant="ghost" size="sm" disabled={busy} title="Retry the failed job"
                    onClick={() => run(() => api.retryJob(job.id))}>
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
          {doc.current_version > 0 && !active && (
            <Button variant="ghost" size="sm" disabled={busy} title="Re-ingest (new version)"
                    onClick={() => run(() => api.reingestDocument(doc.id))}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          )}
          {confirming ? (
            <>
              <Button variant="destructive" size="sm" disabled={busy}
                      onClick={() => run(() => api.deleteDocument(doc.id))}>
                Delete
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>Cancel</Button>
            </>
          ) : (
            <Button variant="ghost" size="sm" title="Delete document" onClick={() => setConfirming(true)}>
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {active && (
        <div className="px-4 pb-3">
          <div className="h-1 overflow-hidden rounded-full bg-zinc-800">
            <div className="h-full bg-sky-400 transition-all duration-500"
                 style={{ width: `${Math.max(3, Math.round((job!.progress ?? 0) * 100))}%` }} />
          </div>
        </div>
      )}

      {(doc.error || error) && (
        <p className="flex items-start gap-2 px-4 pb-3 text-xs text-red-400">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {error ?? doc.error}
        </p>
      )}

      {open && doc.current_version > 0 && (
        <div className="border-t border-zinc-800 px-4 py-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs uppercase tracking-wide text-zinc-500">
            <Layers className="h-3.5 w-3.5" /> Section tree
          </p>
          <SectionTree key={`${doc.id}-${doc.current_version}`} documentId={doc.id} />
        </div>
      )}
    </li>
  )
}

export default function LibraryPage() {
  const [collections, setCollections] = useState<Collection[] | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [newName, setNewName] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const loadCollections = useCallback(async () => {
    try {
      const list = await api.listCollections()
      setCollections(list)
      setSelected((cur) => {
        if (cur && list.some((c) => c.id === cur)) return cur
        let last: string | null = null
        try { last = localStorage.getItem(LAST_COLLECTION_KEY) } catch { /* private mode */ }
        return list.find((c) => c.id === last)?.id ?? list[0]?.id ?? null
      })
      setError(null)
    } catch (e) {
      setError(message(e))
      setCollections([])
    }
  }, [])

  const loadDocuments = useCallback(async () => {
    if (!selected) return setDocuments([])
    try {
      setDocuments(await api.listDocuments(selected))
    } catch (e) {
      setError(message(e))
    }
  }, [selected])

  useEffect(() => { loadCollections() }, [loadCollections])
  useEffect(() => {
    loadDocuments()
    if (selected) try { localStorage.setItem(LAST_COLLECTION_KEY, selected) } catch { /* ignore */ }
  }, [selected, loadDocuments])

  // Follow every queued or running job over SSE; refresh the list when one ends.
  const activeJobIds = useMemo(
    () => documents.filter((d) => isActive(d.latest_job)).map((d) => d.latest_job!.id).sort().join(","),
    [documents],
  )
  useEffect(() => {
    if (!activeJobIds) return
    const stops = activeJobIds.split(",").map((jobId) =>
      api.watchJob(
        jobId,
        (job: Job) => setDocuments((docs) =>
          docs.map((d) => (d.latest_job?.id === job.id ? { ...d, latest_job: job } : d))),
        () => { loadDocuments(); loadCollections() },
      ))
    return () => stops.forEach((stop) => stop())
  }, [activeJobIds, loadDocuments, loadCollections])

  const createCollection = async () => {
    const name = newName.trim()
    if (!name) return
    try {
      const col = await api.createCollection(name)
      setNewName("")
      await loadCollections()
      setSelected(col.id)
    } catch (e) {
      setError(message(e))
    }
  }

  const upload = async (files: File[]) => {
    if (!selected || files.length === 0) return
    setUploading(true)
    setError(null)
    setNotice(null)
    try {
      const results = await api.uploadDocuments(selected, files)
      const dupes = results.filter((r) => r.duplicate).map((r) => r.filename)
      const queued = results.length - dupes.length
      setNotice([
        queued ? `${queued} file${queued === 1 ? "" : "s"} queued for ingestion.` : null,
        dupes.length ? `Already in this collection: ${dupes.join(", ")}.` : null,
      ].filter(Boolean).join(" "))
      await Promise.all([loadDocuments(), loadCollections()])
    } catch (e) {
      setError(message(e))
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ""
    }
  }

  const current = collections?.find((c) => c.id === selected) ?? null

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200">
      <header className="border-b border-zinc-900">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white">
              <span className="text-sm font-bold text-zinc-950">C</span>
            </div>
            <span className="font-semibold text-white">CADIS</span>
            <span className="ml-2 text-sm text-zinc-500">Library</span>
          </Link>
          <Link href="/launch" className="text-sm text-zinc-400 hover:text-white">
            Quick try (single document) →
          </Link>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-8 md:grid-cols-[260px_1fr]">
        {/* Collections */}
        <aside>
          <h2 className="mb-3 text-xs uppercase tracking-wide text-zinc-500">Collections</h2>
          <ul className="space-y-1">
            {collections === null && <li className="text-sm text-zinc-600">Loading…</li>}
            {collections?.length === 0 && !error && (
              <li className="text-sm text-zinc-600">No collections yet.</li>
            )}
            {collections?.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => setSelected(c.id)}
                  className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                    c.id === selected ? "bg-zinc-800 text-white" : "text-zinc-400 hover:bg-zinc-900 hover:text-white"
                  }`}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <Folder className="h-4 w-4 shrink-0" />
                    <span className="truncate">{c.name}</span>
                  </span>
                  <span className="text-xs text-zinc-500">{c.document_count}</span>
                </button>
              </li>
            ))}
          </ul>
          <form
            className="mt-4 flex gap-2"
            onSubmit={(e) => { e.preventDefault(); createCollection() }}
          >
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="New collection"
              maxLength={200}
              className="min-w-0 flex-1 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-zinc-600 focus:outline-none"
            />
            <Button type="submit" size="sm" variant="secondary" disabled={!newName.trim()} title="Create collection">
              <FolderPlus className="h-4 w-4" />
            </Button>
          </form>
        </aside>

        {/* Documents */}
        <section className="min-w-0">
          {error && (
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-900/60 bg-red-950/30 px-4 py-3 text-sm text-red-300">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
            </div>
          )}

          {!current ? (
            <div className="rounded-xl border border-dashed border-zinc-800 px-6 py-16 text-center text-sm text-zinc-500">
              {collections?.length ? "Select a collection." : "Create a collection to start adding documents."}
            </div>
          ) : (
            <>
              <h1 className="mb-4 text-2xl font-bold text-white" style={{ fontFamily: "var(--font-cal-sans)" }}>
                {current.name}
              </h1>

              <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragging(false)
                  upload(Array.from(e.dataTransfer.files))
                }}
                onClick={() => !uploading && fileInput.current?.click()}
                className={`mb-2 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-6 py-8 text-center transition-colors ${
                  dragging ? "border-sky-500 bg-sky-950/20" : "border-zinc-800 hover:border-zinc-600"
                }`}
              >
                {uploading ? <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
                           : <Upload className="h-6 w-6 text-zinc-500" />}
                <p className="text-sm text-zinc-300">
                  {uploading ? "Uploading…" : "Drop PDF, DOCX or TXT files here, or click to choose"}
                </p>
                <p className="text-xs text-zinc-600">
                  Several files at once. Ingestion runs in the background — you can close this page.
                </p>
                <input
                  ref={fileInput}
                  type="file"
                  multiple
                  accept={ACCEPT}
                  className="hidden"
                  onChange={(e) => upload(Array.from(e.target.files ?? []))}
                />
              </div>
              {notice && <p className="mb-4 text-xs text-zinc-400">{notice}</p>}

              {documents.length === 0 ? (
                <p className="mt-6 text-sm text-zinc-600">No documents in this collection yet.</p>
              ) : (
                <ul className="mt-4 space-y-2">
                  {documents.map((d) => (
                    <DocumentRow
                      key={d.id}
                      doc={d}
                      onChanged={() => { loadDocuments(); loadCollections() }}
                    />
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  )
}
