"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"

const steps = [
  {
    number: "01",
    name: "Preprocessing",
    model: "spaCy en_core_web_sm",
    description:
      "Raw text is tokenized and split into sentences. Each token receives POS tags, dependency labels, and lemmas for downstream modules.",
    outputs: ["Tokens", "Sentences", "POS Tags", "Dependency Parse"],
  },
  {
    number: "02",
    name: "Embeddings",
    model: "all-MiniLM-L6-v2",
    description:
      "Each sentence is encoded into a 384-dimensional dense vector. Cosine similarity between vectors drives semantic search and ambiguity resolution.",
    outputs: ["384-dim Vectors", "Cosine Similarity", "Semantic Clusters"],
  },
  {
    number: "03",
    name: "NER + IE",
    model: "dslim/bert-base-NER",
    description:
      "BERT-NER identifies named entities — persons, organizations, locations, money, and dates — with confidence scores. SVO triples are extracted via dependency parsing.",
    outputs: ["Entities", "Confidence Scores", "SVO Relations"],
    highlighted: true,
  },
  {
    number: "04",
    name: "Ambiguity Detection",
    model: "MiniLM + spaCy",
    description:
      "PP-attachment ambiguities and anaphoric pronouns are flagged. Embedding similarity against candidate referents resolves each ambiguity contextually.",
    outputs: ["PP Attachments", "Pronoun Referents", "Resolution Confidence"],
  },
  {
    number: "05",
    name: "QA Engine",
    model: "deepset/minilm-uncased-squad2",
    description:
      "Seven auto-generated questions probe who, what, where, when, and how much. Extractive span answers are returned with confidence-filtered results.",
    outputs: ["Span Answers", "7 Questions", "Confidence Filter"],
  },
  {
    number: "06",
    name: "Summarization",
    model: "sshleifer/distilbart-cnn-12-6",
    description:
      "DistilBART generates an abstractive executive summary. Entity-weighted sentence scoring selects key bullets. DATE/TIME entities build a temporal timeline.",
    outputs: ["Executive Summary", "Key Sentences", "Event Timeline"],
  },
]

function BorderBeam() {
  return (
    <div className="absolute inset-0 rounded-2xl overflow-hidden pointer-events-none">
      <div
        className="absolute w-24 h-24 bg-white/20 blur-xl border-beam"
        style={{
          offsetPath: "rect(0 100% 100% 0 round 16px)",
        }}
      />
    </div>
  )
}

export function Pricing() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section id="pipeline" className="py-24 px-4">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2
            className="text-3xl sm:text-4xl font-bold text-white mb-4"
            style={{ fontFamily: "var(--font-instrument-sans)" }}
          >
            The CADIS pipeline
          </h2>
          <p className="text-zinc-400 max-w-2xl mx-auto">
            Six modules run end-to-end on every document. Each step's output becomes context for the next.
          </p>
        </motion.div>

        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 40 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {steps.map((step, index) => (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.3 + index * 0.1 }}
              className={`relative p-6 rounded-2xl border transition-all duration-300 hover:scale-[1.02] ${
                step.highlighted
                  ? "bg-zinc-900 border-zinc-700"
                  : "bg-zinc-900/50 border-zinc-800 hover:border-zinc-600"
              }`}
            >
              {step.highlighted && <BorderBeam />}
              {step.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-white text-zinc-950 text-xs font-medium rounded-full">
                  Core Module
                </div>
              )}

              <div className="mb-4">
                <span className="text-4xl font-bold text-zinc-800 font-mono select-none">{step.number}</span>
              </div>

              <div className="mb-4">
                <h3 className="text-xl font-semibold text-white mb-1">{step.name}</h3>
                <p className="text-xs text-zinc-600 font-mono">{step.model}</p>
              </div>

              <p className="text-zinc-400 text-sm mb-6 leading-relaxed">{step.description}</p>

              <ul className="space-y-2">
                {step.outputs.map((output) => (
                  <li key={output} className="flex items-center gap-2 text-sm text-zinc-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                    {output}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
