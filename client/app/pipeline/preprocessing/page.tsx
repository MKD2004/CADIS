"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import Link from "next/link"
import { PipelineNav } from "@/components/pipeline-nav"
import { ArrowRight } from "lucide-react"

interface TokenDetail { text: string; lemma: string; pos: string; dep: string; is_stop: boolean }
interface Data {
  stats: { total_tokens: number; sentences: number; unique_tokens: number; stop_words: number; char_count: number }
  token_details: TokenDetail[]
  sentences: string[]
}

const POS_COLORS: Record<string, string> = {
  NNP:  "bg-emerald-950/50 text-emerald-400 border-emerald-800/50",
  PROPN:"bg-emerald-950/50 text-emerald-400 border-emerald-800/50",
  NN:   "bg-blue-950/50 text-blue-400 border-blue-800/50",
  NOUN: "bg-blue-950/50 text-blue-400 border-blue-800/50",
  VBD:  "bg-violet-950/50 text-violet-400 border-violet-800/50",
  VBZ:  "bg-violet-950/50 text-violet-400 border-violet-800/50",
  VB:   "bg-violet-950/50 text-violet-400 border-violet-800/50",
  VERB: "bg-violet-950/50 text-violet-400 border-violet-800/50",
  JJ:   "bg-amber-950/50 text-amber-400 border-amber-800/50",
  ADJ:  "bg-amber-950/50 text-amber-400 border-amber-800/50",
  RB:   "bg-pink-950/50 text-pink-400 border-pink-800/50",
  ADV:  "bg-pink-950/50 text-pink-400 border-pink-800/50",
}

const stagger = { hidden: {}, visible: { transition: { staggerChildren: 0.025 } } }
const chip    = { hidden: { opacity: 0, scale: 0.85 }, visible: { opacity: 1, scale: 1, transition: { duration: 0.25 } } }

export default function PreprocessingPage() {
  const router = useRouter()
  const [data, setData] = useState<Data | null>(null)

  useEffect(() => {
    const raw = localStorage.getItem("cadis_result")
    if (!raw) { router.push("/launch"); return }
    setData(JSON.parse(raw).preprocessing)
  }, [router])

  if (!data) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-5 h-5 border border-zinc-700 border-t-white rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="min-h-screen bg-zinc-950">
      <PipelineNav activeIndex={0} />
      <main className="pt-24 pb-20 px-4">
        <div className="max-w-5xl mx-auto">

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
            <span className="inline-block px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 text-xs font-mono mb-4">Module 01</span>
            <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: "var(--font-cal-sans)" }}>Preprocessing</h1>
            <p className="text-zinc-500 font-mono text-sm">spaCy en_core_web_sm · tokenization · POS tagging · dependency parsing</p>
          </motion.div>

          {/* Stats */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: "Tokens",       value: data.stats.total_tokens },
              { label: "Sentences",    value: data.stats.sentences },
              { label: "Unique Words", value: data.stats.unique_tokens },
              { label: "Stop Words",   value: data.stats.stop_words },
            ].map((s) => (
              <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 text-center">
                <div className="text-3xl font-bold text-white font-mono mb-1">{s.value}</div>
                <div className="text-xs text-zinc-500">{s.label}</div>
              </div>
            ))}
          </motion.div>

          {/* Token stream */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6">
            <h2 className="text-white font-semibold mb-1">Token Stream</h2>
            <p className="text-zinc-600 text-xs font-mono mb-4">
              <span className="text-emerald-400">green</span>=proper noun · <span className="text-blue-400">blue</span>=noun · <span className="text-violet-400">violet</span>=verb · <span className="text-amber-400">amber</span>=adjective · <span className="text-pink-400">pink</span>=adverb · hover for POS/dep
            </p>
            <motion.div variants={stagger} initial="hidden" animate="visible" className="flex flex-wrap gap-1.5">
              {data.token_details.map((tok, i) => {
                const cls = POS_COLORS[tok.pos] ?? "bg-zinc-800 text-zinc-400 border-zinc-700"
                return (
                  <motion.span key={i} variants={chip} title={`POS: ${tok.pos} | Dep: ${tok.dep} | Lemma: ${tok.lemma}`}
                    className={`px-2 py-0.5 rounded border text-xs font-mono cursor-default ${cls}`}>
                    {tok.text}
                  </motion.span>
                )
              })}
            </motion.div>
          </motion.div>

          {/* POS table */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6 overflow-x-auto">
            <h2 className="text-white font-semibold mb-4">POS Tag Table <span className="text-zinc-600 text-sm font-normal font-mono">first 25 tokens</span></h2>
            <table className="w-full text-sm font-mono min-w-[560px]">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500 text-xs">
                  {["Token","Lemma","POS","Dep","Stop?"].map(h => <th key={h} className="text-left pb-3 pr-6">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.token_details.slice(0, 25).map((tok, i) => (
                  <tr key={i} className="border-b border-zinc-800/40 hover:bg-zinc-800/20 transition-colors">
                    <td className="py-2 pr-6 text-white">{tok.text}</td>
                    <td className="py-2 pr-6 text-zinc-400">{tok.lemma}</td>
                    <td className="py-2 pr-6">
                      <span className={`px-1.5 py-0.5 rounded text-xs border ${POS_COLORS[tok.pos] ?? "bg-zinc-800 text-zinc-500 border-zinc-700"}`}>{tok.pos}</span>
                    </td>
                    <td className="py-2 pr-6 text-zinc-500">{tok.dep}</td>
                    <td className="py-2 pr-6 text-emerald-500">{tok.is_stop ? "✓" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.div>

          {/* Sentences */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-10">
            <h2 className="text-white font-semibold mb-4">Sentences <span className="text-zinc-600 text-sm font-normal font-mono">({data.sentences.length} total)</span></h2>
            <div className="space-y-3">
              {data.sentences.map((sent, i) => (
                <div key={i} className="flex gap-4 p-4 rounded-xl bg-zinc-800/40 border border-zinc-800">
                  <span className="text-zinc-600 font-mono text-xs mt-0.5 shrink-0">{String(i + 1).padStart(2, "0")}</span>
                  <p className="text-zinc-300 text-sm leading-relaxed">{sent}</p>
                </div>
              ))}
            </div>
          </motion.div>

          <div className="flex justify-end">
            <Link href="/pipeline/embeddings">
              <button className="shimmer-btn flex items-center gap-2 bg-white text-zinc-950 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-200 transition-colors">
                Next: Embeddings <ArrowRight className="w-4 h-4" />
              </button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
