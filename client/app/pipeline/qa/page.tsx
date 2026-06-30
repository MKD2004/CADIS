"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import Link from "next/link"
import { PipelineNav } from "@/components/pipeline-nav"
import { ArrowRight, ArrowLeft, Send, Info } from "lucide-react"

interface QAResult { question: string; answer: string; confidence: number; start: number; end: number }
interface Data {
  results: QAResult[]
  stats: { answered: number; total: number; avg_confidence: number }
}
interface CustomAnswer extends QAResult { loading?: boolean }

function ConfidenceBar({ value, delay = 0 }: { value: number; delay?: number }) {
  const pct = Math.round(value * 100)
  const color = value > 0.5 ? "bg-emerald-500" : value > 0.25 ? "bg-amber-500" : "bg-zinc-500"
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <motion.div className={`h-full ${color} rounded-full`}
          initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ delay, duration: 0.6, ease: [0.22, 1, 0.36, 1] }} />
      </div>
      <span className="text-xs font-mono text-zinc-500 w-8 text-right">{pct}%</span>
    </div>
  )
}

function QACard({ qa, index, delay = 0 }: { qa: QAResult; index: number; delay?: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 hover:border-zinc-700 transition-colors">
      <span className="inline-block px-2 py-0.5 rounded bg-zinc-800 text-zinc-500 text-xs font-mono mb-3">Q{index}</span>
      <p className="text-zinc-400 text-sm mb-3 leading-relaxed">{qa.question}</p>
      {qa.answer ? (
        <>
          <p className="text-white font-semibold text-base leading-snug mb-3">{qa.answer}</p>
          <ConfidenceBar value={qa.confidence} delay={delay + 0.1} />
        </>
      ) : (
        <p className="text-zinc-600 text-sm italic font-mono">No answer found in document</p>
      )}
    </motion.div>
  )
}

export default function QAPage() {
  const router = useRouter()
  const [data, setData] = useState<Data | null>(null)
  const [document, setDocument] = useState("")
  const [customQ, setCustomQ] = useState("")
  const [answers, setAnswers] = useState<CustomAnswer[]>([])
  const [asking, setAsking] = useState(false)
  const [askError, setAskError] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const raw = localStorage.getItem("cadis_result")
    if (!raw) { router.push("/launch"); return }
    setData(JSON.parse(raw).qa)
    setDocument(localStorage.getItem("cadis_document") ?? "")
  }, [router])

  const handleAsk = async () => {
    const q = customQ.trim()
    if (!q || asking) return
    setAskError("")
    setAsking(true)

    const placeholder: CustomAnswer = { question: q, answer: "", confidence: 0, start: 0, end: 0, loading: true }
    setAnswers(prev => [placeholder, ...prev])
    setCustomQ("")

    try {
      const res = await fetch("${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/qa-ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: document, question: q }),
      })
      if (!res.ok) throw new Error((await res.json()).detail ?? "Request failed")
      const result: QAResult = await res.json()
      setAnswers(prev => [{ ...result, loading: false }, ...prev.slice(1)])
    } catch (e: unknown) {
      setAskError(e instanceof Error ? e.message : "Unknown error")
      setAnswers(prev => prev.slice(1))
    } finally {
      setAsking(false)
      inputRef.current?.focus()
    }
  }

  if (!data) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-5 h-5 border border-zinc-700 border-t-white rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950">
      <PipelineNav activeIndex={4} />
      <main className="pt-24 pb-20 px-4">
        <div className="max-w-5xl mx-auto">

          {/* Header */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
            <span className="inline-block px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 text-xs font-mono mb-4">Module 05</span>
            <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: "var(--font-cal-sans)" }}>QA Engine</h1>
            <p className="text-zinc-500 font-mono text-sm">deepset/minilm-uncased-squad2 · extractive span QA · answers from your document only</p>
          </motion.div>

          {/* Stats */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-3 gap-4 mb-6">
            {[
              { label: "Questions Answered", value: `${data.stats.answered} / ${data.stats.total}` },
              { label: "Avg Confidence",     value: `${(data.stats.avg_confidence * 100).toFixed(0)}%` },
              { label: "Method",             value: "Span Extract", mono: true },
            ].map(s => (
              <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 text-center">
                <div className={`text-2xl font-bold text-white mb-1 ${s.mono ? "font-mono text-lg" : ""}`}>{s.value}</div>
                <div className="text-xs text-zinc-500">{s.label}</div>
              </div>
            ))}
          </motion.div>

          {/* Confidence explanation */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
            className="flex items-start gap-2.5 p-4 rounded-xl bg-zinc-900 border border-zinc-800 mb-8 text-xs text-zinc-500 font-mono">
            <Info className="w-3.5 h-3.5 mt-0.5 shrink-0 text-zinc-600" />
            <span>
              Extractive QA confidence is a model-internal span score, not a probability. 20–50% is normal and still means a real answer was located.{" "}
              <span className="text-zinc-400">Asking document-specific questions below will score higher than the generic presets.</span>
            </span>
          </motion.div>

          {/* ── Custom question input ── */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl p-6 mb-8">
            <h2 className="text-white font-semibold mb-1">Ask your own question</h2>
            <p className="text-zinc-600 text-xs font-mono mb-4">
              The model extracts the answer span directly from your document — no hallucination
            </p>

            <div className="flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={customQ}
                onChange={e => setCustomQ(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleAsk()}
                placeholder="e.g. Who signed the agreement? What was the total amount?"
                className="flex-1 bg-zinc-800 border border-zinc-700 focus:border-zinc-500 rounded-xl px-4 py-3 text-white text-sm placeholder-zinc-600 outline-none transition-colors"
              />
              <button
                onClick={handleAsk}
                disabled={!customQ.trim() || asking}
                className={`flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-medium transition-all shrink-0 ${
                  customQ.trim() && !asking
                    ? "bg-white text-zinc-950 hover:bg-zinc-200"
                    : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
                }`}
              >
                {asking
                  ? <span className="w-4 h-4 border border-zinc-400 border-t-zinc-900 rounded-full animate-spin" />
                  : <Send className="w-4 h-4" />
                }
                <span>{asking ? "Asking…" : "Ask"}</span>
              </button>
            </div>

            <AnimatePresence>
              {askError && (
                <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="text-red-400 text-xs font-mono mt-3">{askError}</motion.p>
              )}
            </AnimatePresence>

            {/* Answers from custom questions */}
            <AnimatePresence>
              {answers.length > 0 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-5 space-y-3">
                  {answers.map((ans, i) => (
                    <motion.div key={`${ans.question}-${i}`}
                      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                      className="p-4 rounded-xl bg-zinc-800/60 border border-zinc-700">
                      <p className="text-zinc-400 text-sm mb-2 leading-relaxed">{ans.question}</p>
                      {ans.loading ? (
                        <div className="flex items-center gap-2 text-zinc-500 text-sm">
                          <span className="w-3.5 h-3.5 border border-zinc-600 border-t-white rounded-full animate-spin" />
                          Finding answer in document…
                        </div>
                      ) : ans.answer ? (
                        <>
                          <p className="text-white font-semibold text-base mb-3">{ans.answer}</p>
                          <ConfidenceBar value={ans.confidence} />
                        </>
                      ) : (
                        <p className="text-zinc-600 text-sm italic">
                          No answer found — try rephrasing or asking about something explicitly in the document
                        </p>
                      )}
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* ── Preset questions ── */}
          <div className="mb-8">
            <h2 className="text-white font-semibold mb-1">Auto-generated questions</h2>
            <p className="text-zinc-600 text-xs font-mono mb-5">7 generic questions run automatically on every document</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.results.map((qa, i) => (
                <QACard key={i} qa={qa} index={i + 1} delay={0.25 + i * 0.06} />
              ))}
            </div>
          </div>

          {/* Answer spans in document */}
          {document && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
              className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-10">
              <h2 className="text-white font-semibold mb-1">Answer spans in document</h2>
              <p className="text-zinc-600 text-xs font-mono mb-4">Highlighted regions = extracted answer spans · no text invented</p>
              <div className="text-sm text-zinc-400 leading-relaxed font-mono bg-zinc-950 rounded-xl p-4 border border-zinc-800 max-h-64 overflow-y-auto">
                {(() => {
                  const allAnswers = [
                    ...data.results,
                    ...answers.filter(a => !a.loading && a.answer),
                  ]
                  const spans = allAnswers
                    .filter(r => r.answer && r.start < r.end)
                    .map(r => ({ start: r.start, end: r.end }))
                    .sort((a, b) => a.start - b.start)

                  const parts: React.ReactNode[] = []
                  let cursor = 0
                  for (const span of spans) {
                    if (span.start > cursor) parts.push(<span key={`t-${cursor}`}>{document.slice(cursor, span.start)}</span>)
                    if (span.start >= cursor) {
                      parts.push(
                        <mark key={`m-${span.start}`} className="bg-emerald-950/60 text-emerald-300 px-0.5 rounded not-italic">
                          {document.slice(span.start, span.end)}
                        </mark>
                      )
                      cursor = span.end
                    }
                  }
                  if (cursor < document.length) parts.push(<span key="end">{document.slice(cursor)}</span>)
                  return parts
                })()}
              </div>
            </motion.div>
          )}

          <div className="flex justify-between">
            <Link href="/pipeline/ambiguity">
              <button className="flex items-center gap-2 border border-zinc-800 text-zinc-300 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-900 transition-colors">
                <ArrowLeft className="w-4 h-4" /> Ambiguity
              </button>
            </Link>
            <Link href="/pipeline/summary">
              <button className="shimmer-btn flex items-center gap-2 bg-white text-zinc-950 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-200 transition-colors">
                Next: Summary <ArrowRight className="w-4 h-4" />
              </button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
