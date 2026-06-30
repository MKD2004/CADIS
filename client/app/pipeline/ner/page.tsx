"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import Link from "next/link"
import { PipelineNav } from "@/components/pipeline-nav"
import { ArrowRight, ArrowLeft } from "lucide-react"

interface Entity { text: string; score: number }
interface Relation { subject: string; verb: string; object: string; sentence: string }
interface Data {
  entities: Record<string, Entity[]>
  relations: Relation[]
  stats: { total_entities: number; entity_types: number; total_relations: number }
}

const TYPE_STYLES: Record<string, { badge: string; bar: string }> = {
  PERSON:       { badge: "bg-blue-950/50 text-blue-400 border-blue-800/50",     bar: "bg-blue-500" },
  ORGANIZATION: { badge: "bg-violet-950/50 text-violet-400 border-violet-800/50", bar: "bg-violet-500" },
  LOCATION:     { badge: "bg-amber-950/50 text-amber-400 border-amber-800/50",  bar: "bg-amber-500" },
  DATE:         { badge: "bg-zinc-800 text-zinc-300 border-zinc-700",           bar: "bg-zinc-400" },
  MONEY:        { badge: "bg-emerald-950/50 text-emerald-400 border-emerald-800/50", bar: "bg-emerald-500" },
  MISC:         { badge: "bg-zinc-800 text-zinc-500 border-zinc-700",           bar: "bg-zinc-500" },
}

export default function NerPage() {
  const router = useRouter()
  const [data, setData] = useState<Data | null>(null)

  useEffect(() => {
    const raw = localStorage.getItem("cadis_result")
    if (!raw) { router.push("/launch"); return }
    setData(JSON.parse(raw).ner)
  }, [router])

  if (!data) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-5 h-5 border border-zinc-700 border-t-white rounded-full animate-spin" />
    </div>
  )

  const entityTypes = Object.entries(data.entities).filter(([, v]) => v.length > 0)

  return (
    <div className="min-h-screen bg-zinc-950">
      <PipelineNav activeIndex={2} />
      <main className="pt-24 pb-20 px-4">
        <div className="max-w-5xl mx-auto">

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
            <span className="inline-block px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 text-xs font-mono mb-4">Module 03</span>
            <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: "var(--font-cal-sans)" }}>NER + IE</h1>
            <p className="text-zinc-500 font-mono text-sm">dslim/bert-base-NER · named entity recognition · SVO relation extraction</p>
          </motion.div>

          {/* Stats */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-3 gap-4 mb-8">
            {[
              { label: "Total Entities",  value: data.stats.total_entities },
              { label: "Entity Types",    value: data.stats.entity_types },
              { label: "Relations Found", value: data.stats.total_relations },
            ].map(s => (
              <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 text-center">
                <div className="text-3xl font-bold text-white font-mono mb-1">{s.value}</div>
                <div className="text-xs text-zinc-500">{s.label}</div>
              </div>
            ))}
          </motion.div>

          {/* Entities */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6">
            <h2 className="text-white font-semibold mb-6">Named Entities</h2>
            <div className="space-y-8">
              {entityTypes.map(([type, ents], gi) => {
                const style = TYPE_STYLES[type] ?? TYPE_STYLES.MISC
                return (
                  <motion.div key={type} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 + gi * 0.08 }}>
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-mono font-semibold border ${style.badge}`}>{type}</span>
                      <span className="text-zinc-600 text-xs font-mono">{ents.length} found</span>
                    </div>
                    <div className="space-y-2">
                      {ents.map((ent, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <span className="text-sm text-zinc-300 w-40 shrink-0 truncate">{ent.text}</span>
                          <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                            <motion.div className={`h-full ${style.bar} rounded-full`}
                              initial={{ width: 0 }} animate={{ width: `${ent.score * 100}%` }}
                              transition={{ delay: 0.3 + i * 0.06, duration: 0.6, ease: [0.22, 1, 0.36, 1] }} />
                          </div>
                          <span className="text-xs font-mono text-zinc-500 w-10 text-right">{(ent.score * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )
              })}
              {entityTypes.length === 0 && (
                <p className="text-zinc-600 font-mono text-sm text-center py-8">No named entities detected</p>
              )}
            </div>
          </motion.div>

          {/* Relations */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-10">
            <h2 className="text-white font-semibold mb-4">Subject — Verb — Object Relations</h2>
            {data.relations.length > 0 ? (
              <div className="space-y-3">
                {data.relations.map((rel, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 + i * 0.06 }}
                    className="p-4 rounded-xl bg-zinc-800/40 border border-zinc-800">
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      <span className="px-2.5 py-1 rounded-lg bg-emerald-950/50 border border-emerald-800/50 text-emerald-400 text-sm font-medium">{rel.subject}</span>
                      <span className="text-zinc-500 text-sm font-mono">—</span>
                      <span className="px-2.5 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400 text-sm font-medium italic">{rel.verb}</span>
                      <span className="text-zinc-500 text-sm font-mono">—</span>
                      <span className="px-2.5 py-1 rounded-lg bg-zinc-800 border border-zinc-700 text-white text-sm font-medium">{rel.object}</span>
                    </div>
                    <p className="text-zinc-600 text-xs font-mono leading-relaxed">{rel.sentence}</p>
                  </motion.div>
                ))}
              </div>
            ) : (
              <p className="text-zinc-600 font-mono text-sm text-center py-8">No SVO relations found</p>
            )}
          </motion.div>

          <div className="flex justify-between">
            <Link href="/pipeline/embeddings">
              <button className="flex items-center gap-2 border border-zinc-800 text-zinc-300 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-900 transition-colors">
                <ArrowLeft className="w-4 h-4" /> Embeddings
              </button>
            </Link>
            <Link href="/pipeline/ambiguity">
              <button className="shimmer-btn flex items-center gap-2 bg-white text-zinc-950 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-200 transition-colors">
                Next: Ambiguity <ArrowRight className="w-4 h-4" />
              </button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
