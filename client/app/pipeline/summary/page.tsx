"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import Link from "next/link"
import { PipelineNav } from "@/components/pipeline-nav"
import { ArrowLeft, CheckCircle, Clock } from "lucide-react"

interface Data {
  executive: string
  key_sentences: string[]
  timeline: { time: string; event: string }[]
  stats: { original_words: number; summary_words: number; compression: string; key_sentences: number; timeline_events: number }
}

export default function SummaryPage() {
  const router = useRouter()
  const [data, setData] = useState<Data | null>(null)

  useEffect(() => {
    const raw = localStorage.getItem("cadis_result")
    if (!raw) { router.push("/launch"); return }
    setData(JSON.parse(raw).summary)
  }, [router])

  if (!data) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-5 h-5 border border-zinc-700 border-t-white rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950">
      <PipelineNav activeIndex={5} />
      <main className="pt-24 pb-20 px-4">
        <div className="max-w-5xl mx-auto">

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
            <span className="inline-block px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 text-xs font-mono mb-4">Module 06</span>
            <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: "var(--font-cal-sans)" }}>Summarization</h1>
            <p className="text-zinc-500 font-mono text-sm">sshleifer/distilbart-cnn-12-6 · abstractive + extractive · timeline anchoring</p>
          </motion.div>

          {/* Stats */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
            {[
              { label: "Key Sentences",   value: data.stats.key_sentences },
              { label: "Timeline Events", value: data.stats.timeline_events },
              { label: "Compression",     value: data.stats.compression },
            ].map(s => (
              <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 text-center">
                <div className="text-3xl font-bold text-white font-mono mb-1">{s.value}</div>
                <div className="text-xs text-zinc-500">{s.label}</div>
              </div>
            ))}
          </motion.div>

          {/* Executive summary */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-white font-semibold">Executive Summary</h2>
              <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-500 text-xs font-mono">DistilBART</span>
            </div>
            <p className="text-zinc-200 text-lg leading-relaxed">{data.executive}</p>
          </motion.div>

          {/* Key sentences */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6">
            <h2 className="text-white font-semibold mb-4">Key Sentences <span className="text-zinc-600 text-sm font-normal font-mono">entity-density ranked</span></h2>
            <div className="space-y-3">
              {data.key_sentences.map((sent, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.35 + i * 0.08 }}
                  className="flex gap-4 p-4 rounded-xl bg-zinc-800/40 border-l-2 border-zinc-600 border border-zinc-800">
                  <span className="text-zinc-600 font-mono text-xs mt-0.5 shrink-0">{String(i + 1).padStart(2, "0")}</span>
                  <p className="text-zinc-300 text-sm leading-relaxed">{sent}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Timeline */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-8">
            <h2 className="text-white font-semibold mb-6 flex items-center gap-2">
              <Clock className="w-4 h-4 text-zinc-500" strokeWidth={1.5} />
              Event Timeline
            </h2>
            {data.timeline.length > 0 ? (
              <div className="relative">
                <div className="absolute left-4 top-0 bottom-0 w-px bg-zinc-800" />
                <div className="space-y-6">
                  {data.timeline.map((item, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 + i * 0.1 }}
                      className="flex gap-6 pl-10 relative">
                      <div className="absolute left-2.5 top-1.5 w-3 h-3 rounded-full bg-zinc-900 border-2 border-emerald-500" />
                      <div>
                        <span className="inline-block px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 text-xs font-mono mb-2">{item.time}</span>
                        <p className="text-zinc-300 text-sm leading-relaxed">{item.event}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-zinc-600 font-mono text-sm text-center py-6">No temporal events detected</p>
            )}
          </motion.div>

          {/* Compression stats */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-8">
            <h2 className="text-white font-semibold mb-4">Compression Statistics</h2>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-white font-mono">{data.stats.original_words}</div>
                <div className="text-xs text-zinc-500">Original Words</div>
              </div>
              <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden relative">
                <motion.div className="h-full bg-white rounded-full"
                  initial={{ width: "100%" }} animate={{ width: `${100 - parseInt(data.stats.compression)}%` }}
                  transition={{ delay: 0.5, duration: 0.8 }} />
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-emerald-400 font-mono">{data.stats.summary_words}</div>
                <div className="text-xs text-zinc-500">Summary Words</div>
              </div>
            </div>
            <p className="text-center text-xs text-zinc-600 font-mono mt-3">{data.stats.compression} compression achieved</p>
          </motion.div>

          {/* Pipeline complete banner */}
          <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.6, duration: 0.5 }}
            className="relative overflow-hidden rounded-2xl border border-emerald-900/50 bg-emerald-950/20 p-8 text-center mb-10">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-950/30 to-transparent pointer-events-none" />
            <div className="relative z-10">
              <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-4" strokeWidth={1.5} />
              <h2 className="text-white text-2xl font-bold mb-2" style={{ fontFamily: "var(--font-cal-sans)" }}>Pipeline Complete</h2>
              <p className="text-zinc-400 text-sm max-w-md mx-auto">
                All 6 modules finished. Your document has been tokenized, embedded, entity-extracted, ambiguity-resolved, QA-answered, and summarized using real ML models.
              </p>
            </div>
          </motion.div>

          <div className="flex justify-between">
            <Link href="/pipeline/qa">
              <button className="flex items-center gap-2 border border-zinc-800 text-zinc-300 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-900 transition-colors">
                <ArrowLeft className="w-4 h-4" /> QA Engine
              </button>
            </Link>
            <Link href="/launch">
              <button className="flex items-center gap-2 border border-zinc-800 text-zinc-300 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-900 transition-colors">
                ← Analyze Another Document
              </button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
