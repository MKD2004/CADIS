"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import Link from "next/link"
import { PipelineNav } from "@/components/pipeline-nav"
import { ArrowRight, ArrowLeft } from "lucide-react"

interface Pair { a: string; b: string; score: number }
interface Position { sentence: string; x: number; y: number }
interface VecRow { sentence: string; dim0: number; dim1: number; dim2: number; norm: number }
interface Data {
  sentences: string[]; dims: number; similarity_matrix: number[][]
  top_pairs: Pair[]; positions: Position[]; vector_preview: VecRow[]
}

export default function EmbeddingsPage() {
  const router = useRouter()
  const [data, setData] = useState<Data | null>(null)
  const [hovered, setHovered] = useState<number | null>(null)

  useEffect(() => {
    const raw = localStorage.getItem("cadis_result")
    if (!raw) { router.push("/launch"); return }
    setData(JSON.parse(raw).embeddings)
  }, [router])

  if (!data) return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="w-5 h-5 border border-zinc-700 border-t-white rounded-full animate-spin" />
    </div>
  )

  // Normalize positions to 0-100 range for SVG
  const xs = data.positions.map(p => p.x)
  const ys = data.positions.map(p => p.y)
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const norm = (v: number, min: number, max: number) =>
    max === min ? 50 : 10 + ((v - min) / (max - min)) * 80

  return (
    <div className="min-h-screen bg-zinc-950">
      <PipelineNav activeIndex={1} />
      <main className="pt-24 pb-20 px-4">
        <div className="max-w-5xl mx-auto">

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
            <span className="inline-block px-3 py-1 rounded-full bg-zinc-800 text-zinc-400 text-xs font-mono mb-4">Module 02</span>
            <h1 className="text-4xl sm:text-5xl font-bold text-white mb-2" style={{ fontFamily: "var(--font-cal-sans)" }}>Embeddings</h1>
            <p className="text-zinc-500 font-mono text-sm">all-MiniLM-L6-v2 · {data.dims}-dim dense vectors · cosine similarity</p>
          </motion.div>

          {/* Stats */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="grid grid-cols-3 gap-4 mb-8">
            {[
              { label: "Sentences Encoded", value: data.sentences.length },
              { label: "Vector Dimensions",  value: data.dims },
              { label: "Similarity Pairs",   value: data.top_pairs.length },
            ].map(s => (
              <div key={s.label} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 text-center">
                <div className="text-3xl font-bold text-white font-mono mb-1">{s.value}</div>
                <div className="text-xs text-zinc-500">{s.label}</div>
              </div>
            ))}
          </motion.div>

          {/* Vector space scatter */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6">
            <h2 className="text-white font-semibold mb-1">Vector Space</h2>
            <p className="text-zinc-600 text-xs font-mono mb-4">2D projection of {data.dims}-dim sentence embeddings (dim[0] × dim[1]) · hover dots to preview</p>
            <div className="relative">
              <svg viewBox="0 0 100 100" className="w-full h-72 rounded-xl bg-zinc-950 border border-zinc-800">
                {/* Grid lines */}
                {[25,50,75].map(v => (
                  <g key={v}>
                    <line x1={v} y1="0" x2={v} y2="100" stroke="#27272a" strokeWidth="0.3" />
                    <line x1="0" y1={v} x2="100" y2={v} stroke="#27272a" strokeWidth="0.3" />
                  </g>
                ))}
                {/* Dots */}
                {data.positions.map((p, i) => {
                  const cx = norm(p.x, minX, maxX)
                  const cy = norm(p.y, minY, maxY)
                  return (
                    <motion.circle key={i} cx={cx} cy={cy} r="2.5"
                      fill={hovered === i ? "#ffffff" : "#52525b"}
                      stroke={hovered === i ? "#fff" : "#3f3f46"}
                      strokeWidth="0.5"
                      initial={{ scale: 0 }} animate={{ scale: 1 }}
                      transition={{ delay: 0.3 + i * 0.1 }}
                      onMouseEnter={() => setHovered(i)}
                      onMouseLeave={() => setHovered(null)}
                      className="cursor-pointer"
                    />
                  )
                })}
              </svg>
              {hovered !== null && (
                <div className="absolute top-2 left-2 max-w-xs p-3 rounded-xl bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 font-mono pointer-events-none">
                  {data.positions[hovered].sentence.slice(0, 120)}{data.positions[hovered].sentence.length > 120 ? "…" : ""}
                </div>
              )}
            </div>
            <p className="text-zinc-600 text-xs font-mono mt-2">Hover dots to preview sentences · {data.positions.length} sentences shown</p>
          </motion.div>

          {/* Vector preview table */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6 overflow-x-auto">
            <h2 className="text-white font-semibold mb-4">Embedding Vector Preview</h2>
            <table className="w-full text-xs font-mono min-w-[560px]">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500">
                  {["Sentence","dim[0]","dim[1]","dim[2]","L2 Norm"].map(h => <th key={h} className="text-left pb-3 pr-4">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.vector_preview.map((row, i) => (
                  <tr key={i} className="border-b border-zinc-800/40 hover:bg-zinc-800/20 transition-colors">
                    <td className="py-2 pr-4 text-zinc-300 max-w-[200px] truncate">{row.sentence}</td>
                    <td className="py-2 pr-4 text-emerald-400">{row.dim0}</td>
                    <td className="py-2 pr-4 text-blue-400">{row.dim1}</td>
                    <td className="py-2 pr-4 text-violet-400">{row.dim2}</td>
                    <td className="py-2 pr-4 text-zinc-400">{row.norm}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.div>

          {/* Similarity matrix */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-6">
            <h2 className="text-white font-semibold mb-4">Cosine Similarity Matrix</h2>
            <div className="overflow-x-auto">
              <table className="text-xs font-mono">
                <tbody>
                  {data.similarity_matrix.map((row, i) => (
                    <tr key={i}>
                      {row.map((val, j) => {
                        const intensity = Math.round(val * 255)
                        const bg = i === j ? "#18181b" : `rgba(16,185,129,${val * 0.6})`
                        return (
                          <td key={j} className="w-14 h-10 text-center border border-zinc-800/50 rounded"
                            style={{ background: bg, color: val > 0.5 ? "#fff" : "#71717a" }}
                            title={`S${i+1} × S${j+1} = ${val.toFixed(3)}`}>
                            {val.toFixed(2)}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>

          {/* Top pairs */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-10">
            <h2 className="text-white font-semibold mb-4">Top Similar Sentence Pairs</h2>
            <div className="space-y-4">
              {data.top_pairs.map((pair, i) => (
                <div key={i} className="p-4 rounded-xl bg-zinc-800/40 border border-zinc-800">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs font-mono text-zinc-500">Pair {i + 1}</span>
                    <span className="text-xs font-mono text-emerald-400">{(pair.score * 100).toFixed(1)}% similarity</span>
                  </div>
                  <p className="text-zinc-300 text-sm mb-2 leading-relaxed">"{pair.a}"</p>
                  <div className="h-0.5 bg-zinc-700 rounded my-2" />
                  <p className="text-zinc-400 text-sm leading-relaxed">"{pair.b}"</p>
                  <div className="mt-3 h-1 bg-zinc-800 rounded-full overflow-hidden">
                    <motion.div className="h-full bg-emerald-500 rounded-full"
                      initial={{ width: 0 }} animate={{ width: `${pair.score * 100}%` }} transition={{ delay: 0.4 + i * 0.1, duration: 0.6 }} />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          <div className="flex justify-between">
            <Link href="/pipeline/preprocessing">
              <button className="flex items-center gap-2 border border-zinc-800 text-zinc-300 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-900 transition-colors">
                <ArrowLeft className="w-4 h-4" /> Preprocessing
              </button>
            </Link>
            <Link href="/pipeline/ner">
              <button className="shimmer-btn flex items-center gap-2 bg-white text-zinc-950 rounded-full px-8 h-11 font-medium text-sm hover:bg-zinc-200 transition-colors">
                Next: NER + IE <ArrowRight className="w-4 h-4" />
              </button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
