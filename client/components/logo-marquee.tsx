"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"

const models = [
  { name: "BERT-NER", width: 100 },
  { name: "MiniLM", width: 80 },
  { name: "RoBERTa", width: 90 },
  { name: "DistilBART", width: 100 },
  { name: "spaCy", width: 70 },
  { name: "HuggingFace", width: 110 },
  { name: "PyTorch", width: 90 },
  { name: "sentence-transformers", width: 180 },
]

export function LogoMarquee() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="py-16 overflow-hidden">
      <motion.div
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ duration: 0.6 }}
        className="text-center mb-10"
      >
        <p className="text-sm text-zinc-500 uppercase tracking-wider font-medium">Powered by leading ML models</p>
      </motion.div>

      <div className="relative">
        {/* Fade masks */}
        <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-zinc-950 to-transparent z-10 pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-zinc-950 to-transparent z-10 pointer-events-none" />

        {/* Marquee container */}
        <div className="flex animate-marquee">
          {[...models, ...models].map((model, index) => (
            <div
              key={index}
              className="flex items-center justify-center min-w-[180px] h-16 mx-8 grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all duration-300"
            >
              <div className="flex items-center gap-2 text-zinc-400">
                <div className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center">
                  <span className="text-xs font-bold">{model.name[0]}</span>
                </div>
                <span className="font-medium font-mono text-sm" style={{ fontFamily: "var(--font-instrument-sans)" }}>
                  {model.name}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
