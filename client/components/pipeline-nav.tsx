"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { Check } from "lucide-react"

const steps = [
  { label: "Preprocessing", route: "/pipeline/preprocessing" },
  { label: "Embeddings", route: "/pipeline/embeddings" },
  { label: "NER + IE", route: "/pipeline/ner" },
  { label: "Ambiguity", route: "/pipeline/ambiguity" },
  { label: "QA Engine", route: "/pipeline/qa" },
  { label: "Summary", route: "/pipeline/summary" },
]

interface PipelineNavProps {
  activeIndex: number
}

export function PipelineNav({ activeIndex }: PipelineNavProps) {
  return (
    <motion.header
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="fixed top-0 left-0 right-0 z-50 bg-zinc-900/60 backdrop-blur-md border-b border-zinc-800"
    >
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <div className="w-7 h-7 rounded-lg bg-white flex items-center justify-center">
            <span className="text-zinc-950 font-bold text-xs">C</span>
          </div>
          <span className="font-semibold text-white text-sm hidden sm:block">CADIS</span>
        </Link>

        {/* Steps */}
        <div className="flex items-center gap-0 flex-1 justify-center">
          {steps.map((step, i) => {
            const isCompleted = i < activeIndex
            const isActive = i === activeIndex

            const Circle = () => (
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono font-bold shrink-0 transition-colors ${
                  isCompleted
                    ? "bg-emerald-500 text-white"
                    : isActive
                    ? "bg-white text-zinc-950"
                    : "bg-zinc-800 text-zinc-600"
                }`}
              >
                {isCompleted ? <Check className="w-3.5 h-3.5" strokeWidth={2.5} /> : i + 1}
              </div>
            )

            return (
              <div key={step.label} className="flex items-center">
                <div className="flex flex-col items-center gap-1">
                  {isCompleted ? (
                    <Link href={step.route} className="hover:opacity-80 transition-opacity">
                      <Circle />
                    </Link>
                  ) : (
                    <Circle />
                  )}
                  <span
                    className={`hidden lg:block text-[10px] font-mono whitespace-nowrap transition-colors ${
                      isActive ? "text-white" : isCompleted ? "text-emerald-500" : "text-zinc-600"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div
                    className={`h-px w-6 sm:w-8 lg:w-12 mx-1 transition-colors ${
                      i < activeIndex ? "bg-emerald-500/50" : "bg-zinc-800"
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>

        {/* Step counter */}
        <span className="text-xs text-zinc-500 font-mono shrink-0">
          Step {activeIndex + 1} of 6
        </span>
      </div>
    </motion.header>
  )
}
