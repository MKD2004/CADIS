"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import Link from "next/link"
import { PipelineNav } from "@/components/pipeline-nav"
import { ArrowRight, ArrowLeft, CheckCircle } from "lucide-react"

interface AmbItem { type: string; trigger: string; sentence: string; candidates: string[]; resolved: string; confidence: number }
interface Data {
  items: AmbItem[]
  stats: { detected: number; pp_attachments: number; anaphoric: number; resolved: number }
}

export default function AmbiguityPage() {
  const router = useRouter()
  const [data, setData] = useState<Data | null>(null)

  useEffect(() => {
    const raw = localStorage.getItem("cadis_result")
    if (!raw) { router.push("/launch"); return }
    setData(JSON.parse(raw).ambiguity)
  }, [router])

  if (!data) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-5 h-5 border border-zinc-700 border-t-white rounded-full animate-spin" />
    </div>
  )

  // Highlight trigger word in sentence
  const highlightTrigger = (sentence: string, trigger: string) => {
    const idx = sentence.toLowerCase().indexOf(trigger.toLowerCase())
    if (idx === -1) return <span className="text-zinc-300 text-sm leading-relaxed">{sentence}</span>
    return (
      <span className="text-zinc-300 text-sm leading-relaxed">
        {sentence.slice(0, idx)}
        <span className="text-amber-400 font-semibold bg-amber-950/40 px-0.5 rounded">{sentence.slice(idx, idx + trigger.length)}</span>
        {sentence.slice(idx + trigger.length)}
      </span>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      <PipelineNav activeIndex={3} />
      <main className="pt-24 pb-20 px-4">
        <div className="max-w-5xl mx-auto">

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
            <span className="inline-block px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 text-xs font-mono mb-4">Module 04</span>
            <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: "var(--font-cal-sans)" }}>
              Ambiguity<br /><span className="text-zinc-500">Resolution</span>
            </h1>
            <p className="text-zinc-500 font-mono text-sm">MiniLM + spaCy · PP attachment · anaphora · cosine similarity resolution</p>
          </motion.div>

          {/* Stats */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: "Detected",      value: data.stats.detected },
              { label: "PP Attachments",value: data.stats.pp_attachments },
              { label: "Anaphoric",     value: data.stats.anaphoric },
              { label: "Resolved",      value: data.stats.resolved, highlight: true },
            ].map(s => (
              <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 text-center">
                <div className={`text-3xl font-bold font-mono mb-1 ${s.highlight ? "text-emerald-400" : "text-white"}`}>{s.value}</div>
                <div className="text-xs text-zinc-500">{s.label}</div>
              </div>
            ))}
          </motion.div>

          {/* Ambiguity cards */}
          {data.items.length === 0 ? (
            <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }}
              className="bg-zinc-900 border border-zinc-800 rounded-2xl p-16 text-center mb-10">
              <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto mb-4" strokeWidth={1.5} />
              <p className="text-white font-semibold text-lg mb-2">No ambiguities detected</p>
              <p className="text-zinc-600 text-sm font-mono">The document structure is unambiguous</p>
            </motion.div>
          ) : (
            <div className="space-y-4 mb-10">
              {data.items.map((amb, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 + i * 0.1 }}
                  className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
                  {/* Type + trigger */}
                  <div className="flex items-center gap-3 mb-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-mono font-semibold border ${
                      amb.type === "PP Attachment"
                        ? "bg-amber-950/50 text-amber-400 border-amber-800/50"
                        : "bg-blue-950/50 text-blue-400 border-blue-800/50"
                    }`}>{amb.type}</span>
                    <span className="text-zinc-600 text-xs font-mono">trigger: <span className="text-amber-400">{amb.trigger}</span></span>
                  </div>

                  {/* Sentence with highlight */}
                  <div className="p-4 rounded-xl bg-zinc-800/50 border border-zinc-800 mb-4 leading-relaxed">
                    {highlightTrigger(amb.sentence, amb.trigger)}
                  </div>

                  {/* Candidates */}
                  <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <span className="text-zinc-600 text-xs font-mono">Candidates:</span>
                    {amb.candidates.map((c, ci) => (
                      <span key={ci} className="flex items-center gap-2">
                        <span className={`px-3 py-1 rounded-full border text-xs font-mono ${
                          c === amb.resolved
                            ? "bg-emerald-950/50 border-emerald-700 text-emerald-400"
                            : "bg-zinc-800 border-zinc-700 text-zinc-400"
                        }`}>{c}</span>
                        {ci < amb.candidates.length - 1 && <span className="text-zinc-700 text-xs">vs</span>}
                      </span>
                    ))}
                  </div>

                  {/* Resolved */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-zinc-600 text-xs font-mono">Resolved →</span>
                      <span className="px-3 py-1 rounded-full bg-emerald-950/50 border border-emerald-700 text-emerald-400 text-xs font-mono font-semibold">
                        {amb.resolved}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-24 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                        <motion.div className="h-full bg-emerald-500 rounded-full"
                          initial={{ width: 0 }} animate={{ width: `${amb.confidence * 100}%` }}
                          transition={{ delay: 0.4 + i * 0.1, duration: 0.6 }} />
                      </div>
                      <span className="text-xs font-mono text-zinc-500">{(amb.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}

          <div className="flex justify-between">
            <Link href="/pipeline/ner">
              <button className="flex items-center gap-2 border border-zinc-800 text-zinc-300 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-900 transition-colors">
                <ArrowLeft className="w-4 h-4" /> NER + IE
              </button>
            </Link>
            <Link href="/pipeline/qa">
              <button className="shimmer-btn flex items-center gap-2 bg-white text-zinc-950 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-200 transition-colors">
                Next: QA Engine <ArrowRight className="w-4 h-4" />
              </button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
