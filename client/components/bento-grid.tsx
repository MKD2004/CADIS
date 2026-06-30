"use client"

import { motion, useInView } from "framer-motion"
import { useRef, useEffect, useState } from "react"
import { FileText, Layers, Tag, GitBranch, MessageSquare, FileStack } from "lucide-react"

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: [0.22, 1, 0.36, 1],
    },
  },
}

function PipelineStatus() {
  const modules = ["Preprocessing", "Embeddings", "NER + IE", "Ambiguity", "QA Engine", "Summary"]
  const [active, setActive] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setActive((prev) => (prev + 1) % modules.length)
    }, 1200)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-col gap-1.5">
      {modules.map((mod, i) => (
        <motion.div
          key={mod}
          className={`flex items-center gap-2 text-xs font-mono transition-colors duration-300 ${
            i === active ? "text-white" : i < active ? "text-emerald-500" : "text-zinc-600"
          }`}
          animate={i === active ? { x: [0, 4, 0] } : {}}
          transition={{ duration: 0.3 }}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              i === active ? "bg-white pulse-glow" : i < active ? "bg-emerald-500" : "bg-zinc-700"
            }`}
          />
          {mod}
        </motion.div>
      ))}
    </div>
  )
}

function TokenStream() {
  const tokens = ["[CLS]", "Apple", "Inc", ".", "announced", "its", "acquisition", "[SEP]"]
  const [visible, setVisible] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setVisible((prev) => (prev >= tokens.length ? 0 : prev + 1))
    }, 400)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {tokens.map((tok, i) => (
        <motion.span
          key={i}
          animate={{ opacity: i < visible ? 1 : 0.1, scale: i < visible ? 1 : 0.9 }}
          transition={{ duration: 0.2 }}
          className={`px-2 py-0.5 text-xs rounded font-mono ${
            tok.startsWith("[") ? "bg-zinc-700 text-zinc-300" : "bg-zinc-800 text-white"
          }`}
        >
          {tok}
        </motion.span>
      ))}
    </div>
  )
}

function ConfidenceChart() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })

  const bars = [
    { label: "Tim Cook", score: 0.97 },
    { label: "Apple Inc.", score: 0.94 },
    { label: "NeuralBase", score: 0.88 },
    { label: "San Francisco", score: 0.85 },
  ]

  return (
    <div ref={ref} className="space-y-2 mt-2">
      {bars.map((bar, i) => (
        <div key={bar.label} className="flex items-center gap-2">
          <span className="text-xs text-zinc-500 w-24 truncate font-mono">{bar.label}</span>
          <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-white rounded-full"
              initial={{ width: 0 }}
              animate={isInView ? { width: `${bar.score * 100}%` } : {}}
              transition={{ duration: 0.8, delay: i * 0.15, ease: [0.22, 1, 0.36, 1] }}
            />
          </div>
          <span className="text-xs text-zinc-400 font-mono w-8">{(bar.score * 100).toFixed(0)}%</span>
        </div>
      ))}
    </div>
  )
}

export function BentoGrid() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section id="features" className="py-24 px-4">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2
            className="text-3xl sm:text-4xl font-bold text-white mb-4"
            style={{ fontFamily: "var(--font-instrument-sans)" }}
          >
            Six intelligent modules
          </h2>
          <p className="text-zinc-400 max-w-2xl mx-auto">
            A full NLP pipeline — from raw text to structured intelligence. Each module runs in sequence, feeding
            context to the next.
          </p>
        </motion.div>

        <motion.div
          ref={ref}
          variants={containerVariants}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {/* Large card — Pipeline Status */}
          <motion.div
            variants={itemVariants}
            className="md:col-span-2 group relative p-6 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-zinc-600 hover:scale-[1.02] transition-all duration-300 overflow-hidden"
          >
            <div className="flex items-start justify-between mb-6">
              <div>
                <div className="p-2 rounded-lg bg-zinc-800 w-fit mb-4">
                  <Layers className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">Full Pipeline Execution</h3>
                <p className="text-zinc-400 text-sm">
                  All six modules run sequentially — each step enriches the context passed to the next, giving you
                  progressively deeper document intelligence.
                </p>
              </div>
              <PipelineStatus />
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4">
              {[
                { label: "Tokens", value: "247" },
                { label: "Entities", value: "18" },
                { label: "Ambiguities", value: "4" },
              ].map((m) => (
                <div key={m.label} className="text-center">
                  <div className="text-2xl font-bold text-white mb-1 font-mono">{m.value}</div>
                  <div className="text-xs text-zinc-500">{m.label}</div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Preprocessing */}
          <motion.div
            variants={itemVariants}
            className="group relative p-6 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-zinc-600 hover:scale-[1.02] transition-all duration-300"
          >
            <div className="p-2 rounded-lg bg-zinc-800 w-fit mb-4">
              <FileText className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Preprocessing</h3>
            <p className="text-zinc-400 text-sm mb-4">
              Tokenization, sentence segmentation, and linguistic annotation via spaCy.
            </p>
            <TokenStream />
          </motion.div>

          {/* NER + IE */}
          <motion.div
            variants={itemVariants}
            className="group relative p-6 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-zinc-600 hover:scale-[1.02] transition-all duration-300"
          >
            <div className="p-2 rounded-lg bg-zinc-800 w-fit mb-4">
              <Tag className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">NER + IE</h3>
            <p className="text-zinc-400 text-sm mb-4">
              BERT-NER extracts persons, organizations, locations, dates, and money with confidence scores.
            </p>
            <ConfidenceChart />
          </motion.div>

          {/* Ambiguity Detection */}
          <motion.div
            variants={itemVariants}
            className="group relative p-6 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-zinc-600 hover:scale-[1.02] transition-all duration-300"
          >
            <div className="p-2 rounded-lg bg-zinc-800 w-fit mb-4">
              <GitBranch className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Ambiguity Resolution</h3>
            <p className="text-zinc-400 text-sm mb-4">
              Detects PP-attachment and anaphoric references, then resolves them with contextual embeddings.
            </p>
            <div className="flex flex-wrap gap-2">
              <span className="px-2 py-1 text-xs bg-zinc-800 rounded text-zinc-400">PP Attachment</span>
              <span className="px-2 py-1 text-xs bg-zinc-800 rounded text-zinc-400">Anaphora</span>
              <span className="px-2 py-1 text-xs bg-zinc-800 rounded text-emerald-500 border border-emerald-900">Resolved</span>
            </div>
          </motion.div>

          {/* QA Engine */}
          <motion.div
            variants={itemVariants}
            className="group relative p-6 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-zinc-600 hover:scale-[1.02] transition-all duration-300"
          >
            <div className="p-2 rounded-lg bg-zinc-800 w-fit mb-4">
              <MessageSquare className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">QA Engine</h3>
            <p className="text-zinc-400 text-sm mb-4">
              Extractive question answering with MiniLM-SQuAD2 across seven auto-generated questions.
            </p>
            <div className="flex items-center gap-2 text-emerald-500 text-sm font-mono">
              <span>7 questions</span>
              <span className="text-zinc-600">·</span>
              <span className="text-zinc-500">span-extraction</span>
            </div>
          </motion.div>

          {/* Summarization */}
          <motion.div
            variants={itemVariants}
            className="group relative p-6 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-zinc-600 hover:scale-[1.02] transition-all duration-300"
          >
            <div className="p-2 rounded-lg bg-zinc-800 w-fit mb-4">
              <FileStack className="w-5 h-5 text-zinc-400" strokeWidth={1.5} />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Summarization</h3>
            <p className="text-zinc-400 text-sm mb-4">
              DistilBART generates an abstractive executive summary, with key sentences and a temporal timeline.
            </p>
            <div className="flex items-center gap-2 text-zinc-400 text-xs font-mono">
              <span className="px-2 py-1 bg-zinc-800 rounded">Abstractive</span>
              <span className="px-2 py-1 bg-zinc-800 rounded">Extractive</span>
              <span className="px-2 py-1 bg-zinc-800 rounded">Timeline</span>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
