"use client"

import { useState, useRef, useCallback } from "react"
import { useRouter } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import { Upload, FileText, X, ArrowRight, ChevronRight, AlertCircle, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"

const SAMPLES = [
  {
    id: "tech",
    label: "Tech M&A",
    tag: "Business",
    tagColor: "text-blue-400 bg-blue-950/50 border-blue-800/50",
    preview: "Apple acquires AI startup NeuralBase for $2.5B…",
    text: `Apple Inc. announced on Tuesday that it will acquire AI startup NeuralBase for $2.5 billion. The deal, expected to close by March 2025, was confirmed by CEO Tim Cook at a press conference held in San Francisco. Legal experts in New York warned that the acquisition might face regulatory scrutiny from the European Commission in Brussels. Sarah Johnson, the CFO, stated that the merger would help Apple expand its AI capabilities significantly. However, she noted that the board had approved the deal on Monday morning after reviewing the contract she was carrying. NeuralBase, founded in 2019 by Dr. Elena Marsh in Boston, had previously raised $400 million in Series C funding led by Sequoia Capital. The startup specializes in large language model compression, enabling on-device inference without cloud dependency. Analysts at Goldman Sachs believe the acquisition price reflects a 12x revenue multiple, consistent with recent AI sector valuations. The European Commission is expected to open a formal inquiry by April 2025, with a ruling anticipated before the end of Q3. Tim Cook emphasized that NeuralBase's technology would be integrated into the next generation of Apple Intelligence features, set for release with iOS 19 in September 2025.`,
  },
  {
    id: "climate",
    label: "Climate Report",
    tag: "Science",
    tagColor: "text-emerald-400 bg-emerald-950/50 border-emerald-800/50",
    preview: "Global temperatures rose 1.4°C above pre-industrial baseline…",
    text: `The Intergovernmental Panel on Climate Change released its landmark assessment in Geneva on October 2024, confirming that global average temperatures have risen 1.4 degrees Celsius above pre-industrial baseline levels. Dr. Priya Nair, lead author from the Indian Institute of Tropical Meteorology, stated that the Arctic region is warming four times faster than the global average. The report highlights that carbon dioxide concentrations reached 424 parts per million in May 2024, the highest level recorded in 3 million years. Scientists at the National Oceanic and Atmospheric Administration observed that 2023 was the hottest year since records began in 1880. The panel recommends that governments must reduce greenhouse gas emissions by 45 percent before 2030 to limit warming to 1.5 degrees Celsius. Professor James Hansen from Columbia University noted that tipping points such as the collapse of the West Antarctic Ice Sheet could be triggered within decades if action is not taken. The European Union pledged to cut emissions by 55 percent by 2030 under the Fit for 55 package, while China announced it would peak carbon emissions before 2025. Extreme weather events, including floods in Pakistan that displaced 8 million people in August 2022 and wildfires burning 900,000 hectares in Canada during summer 2023, are consistent with the projected consequences of climate change.`,
  },
  {
    id: "medical",
    label: "Clinical Trial",
    tag: "Medical",
    tagColor: "text-violet-400 bg-violet-950/50 border-violet-800/50",
    preview: "Phase III trial of drug VX-7890 shows 73% efficacy…",
    text: `A Phase III randomized controlled trial published in the New England Journal of Medicine on January 2025 evaluated the efficacy of the novel mRNA-based therapeutic VX-7890 in patients with treatment-resistant non-small cell lung cancer. The trial enrolled 1,240 patients across 38 clinical sites in the United States, Germany, Japan, and Brazil between March 2022 and September 2024. Principal investigator Dr. Michael Chen from Memorial Sloan Kettering Cancer Center reported that patients receiving VX-7890 showed a 73 percent overall response rate, compared to 28 percent in the control group receiving standard platinum-based chemotherapy. The median progression-free survival in the treatment arm was 14.2 months versus 5.8 months in the control arm, representing a statistically significant improvement with a p-value below 0.001. Adverse events of grade 3 or higher occurred in 22 percent of participants in the VX-7890 group, primarily presenting as immune-related pneumonitis and elevated liver enzymes. Dr. Aisha Patel from the University of Texas MD Anderson Cancer Center noted that biomarker analysis identified high PD-L1 expression as a predictor of exceptional response. The FDA granted VX-7890 Breakthrough Therapy designation in February 2023, and the manufacturer Vertex Oncology submitted a Biologics License Application in November 2024. Analysts project peak annual sales could exceed $8 billion if approved for first-line treatment.`,
  },
  {
    id: "legal",
    label: "Legal Contract",
    tag: "Legal",
    tagColor: "text-amber-400 bg-amber-950/50 border-amber-800/50",
    preview: "Service Agreement between Meridian Corp and DataFlow Inc…",
    text: `This Master Service Agreement is entered into as of January 15, 2025, by and between Meridian Corporation, a Delaware corporation with its principal place of business at 500 Madison Avenue, New York, NY 10022 (hereinafter referred to as the Client), and DataFlow Analytics Inc., a California corporation with its principal place of business at 1 Market Street, San Francisco, CA 94105 (hereinafter referred to as the Service Provider). The Service Provider agrees to deliver cloud-based data processing and machine learning infrastructure services as described in Exhibit A attached hereto. The initial term of this Agreement shall commence on February 1, 2025, and continue for a period of twenty-four months unless earlier terminated pursuant to Section 12. The Client shall pay the Service Provider a monthly retainer of $125,000 due on the first business day of each calendar month. In the event of late payment, the Service Provider may charge interest at the rate of 1.5 percent per month on any outstanding balance. Either party may terminate this Agreement for cause upon thirty days written notice if the other party materially breaches any provision of this Agreement and fails to cure such breach within fifteen days of receiving written notice. The Service Provider represents and warrants that the services shall be performed in a professional and workmanlike manner consistent with industry standards. The Client agrees not to solicit or hire any employee of the Service Provider for a period of twelve months following termination of this Agreement. This Agreement shall be governed by the laws of the State of New York without regard to its conflict of laws provisions.`,
  },
]

const textRevealVariants = {
  hidden: { y: "100%" },
  visible: (i: number) => ({
    y: 0,
    transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: i * 0.12 },
  }),
}

const MODULES = [
  { label: "Preprocessing", model: "spaCy en_core_web_sm" },
  { label: "Embeddings",    model: "all-MiniLM-L6-v2" },
  { label: "NER + IE",      model: "dslim/bert-base-NER" },
  { label: "Ambiguity",     model: "MiniLM + spaCy" },
  { label: "QA Engine",     model: "roberta-base-squad2" },
  { label: "Summary",       model: "distilbart-cnn-12-6" },
]

function LoadingOverlay({ activeModule }: { activeModule: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-zinc-950/95 backdrop-blur-sm flex flex-col items-center justify-center px-4"
    >
      <div className="noise-overlay" aria-hidden="true" />
      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-10">
          <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
            <span className="text-zinc-950 font-bold text-sm">C</span>
          </div>
          <span className="font-semibold text-white">CADIS</span>
        </div>

        <h2 className="text-center text-white text-2xl font-bold mb-2" style={{ fontFamily: "var(--font-cal-sans)" }}>
          Running Pipeline
        </h2>
        <p className="text-center text-zinc-500 text-sm mb-10 font-mono">
          {activeModule < MODULES.length
            ? `Loading ${MODULES[activeModule].model}…`
            : "Finalizing results…"}
        </p>

        {/* Module steps */}
        <div className="space-y-3">
          {MODULES.map((mod, i) => {
            const done    = i < activeModule
            const current = i === activeModule
            const pending = i > activeModule
            return (
              <motion.div
                key={mod.label}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.07 }}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-500 ${
                  current
                    ? "bg-zinc-900 border-zinc-600"
                    : done
                    ? "bg-zinc-900/40 border-zinc-800"
                    : "bg-transparent border-zinc-900"
                }`}
              >
                {/* Status dot */}
                <div className={`w-2 h-2 rounded-full shrink-0 ${
                  done    ? "bg-emerald-500"
                  : current ? "bg-white pulse-glow"
                  : "bg-zinc-700"
                }`} />

                <div className="flex-1 min-w-0">
                  <span className={`text-sm font-medium ${
                    done ? "text-emerald-400" : current ? "text-white" : "text-zinc-600"
                  }`}>
                    {mod.label}
                  </span>
                  {current && (
                    <span className="ml-2 text-xs text-zinc-500 font-mono">{mod.model}</span>
                  )}
                </div>

                {done && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="text-xs text-emerald-500 font-mono"
                  >
                    ✓
                  </motion.span>
                )}
                {current && (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    className="w-3.5 h-3.5 border border-zinc-600 border-t-white rounded-full"
                  />
                )}
              </motion.div>
            )
          })}
        </div>

        {/* Progress bar */}
        <div className="mt-8 h-0.5 bg-zinc-800 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-white rounded-full"
            animate={{ width: `${(activeModule / MODULES.length) * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
        <p className="text-center text-xs text-zinc-600 mt-3 font-mono">
          {activeModule} / {MODULES.length} modules complete
        </p>
      </div>
    </motion.div>
  )
}

export default function LaunchPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [fileContent, setFileContent] = useState("")
  const [text, setText] = useState("")
  const [dragging, setDragging] = useState(false)
  const [mode, setMode] = useState<"upload" | "paste" | "sample">("upload")
  const [selectedSample, setSelectedSample] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeModule, setActiveModule] = useState(0)
  const [error, setError] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const ACCEPTED = [".txt", ".pdf", ".docx"]
  const isAccepted = (f: File) => ACCEPTED.some(ext => f.name.toLowerCase().endsWith(ext))

  const extractAndSet = async (f: File) => {
    setError("")
    if (f.name.toLowerCase().endsWith(".txt")) {
      const reader = new FileReader()
      reader.onload = (e) => setFileContent(e.target?.result as string ?? "")
      reader.readAsText(f)
    } else {
      // PDF / DOCX — send to backend for text extraction
      setFileContent("") // clear while extracting
      const form = new FormData()
      form.append("file", f)
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/extract`, { method: "POST", body: form })
        if (!res.ok) {
          const err = await res.json()
          setError(err.detail ?? "Extraction failed")
          setFile(null)
          return
        }
        const data = await res.json()
        setFileContent(data.text)
      } catch {
        setError("Cannot reach CADIS API. Start it with: uvicorn api_server:app --port 8000")
        setFile(null)
      }
    }
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped && isAccepted(dropped)) {
      setFile(dropped)
      extractAndSet(dropped)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files?.[0]
    if (picked) { setFile(picked); extractAndSet(picked) }
  }

  const loadSample = (id: string) => {
    setSelectedSample(id)
    setError("")
  }

  const ready = mode === "upload"
    ? (!!file && !!fileContent)
    : mode === "paste"
    ? text.trim().length > 20
    : !!selectedSample

  const handleRun = async () => {
    const doc = mode === "upload"
      ? fileContent
      : mode === "paste"
      ? text
      : SAMPLES.find(s => s.id === selectedSample)?.text ?? ""
    if (!doc.trim()) return

    setError("")
    setLoading(true)
    setActiveModule(0)

    // Tick the loading UI through modules while the real fetch runs
    const ticker = setInterval(() => {
      setActiveModule((prev) => Math.min(prev + 1, MODULES.length - 1))
    }, 4000)

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: doc }),
      })

      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const result = await res.json()

      clearInterval(ticker)
      setActiveModule(MODULES.length)

      localStorage.setItem("cadis_document", doc)
      localStorage.setItem("cadis_result", JSON.stringify(result))

      await new Promise((r) => setTimeout(r, 600)) // brief "complete" flash
      router.push("/pipeline/preprocessing")
    } catch (err: unknown) {
      clearInterval(ticker)
      setLoading(false)
      setActiveModule(0)
      const msg = err instanceof Error ? err.message : "Unknown error"
      if (msg.includes("fetch") || msg.includes("Failed")) {
        setError("Cannot reach the CADIS API. Start it with: uvicorn api_server:app --port 8000")
      } else {
        setError(`Pipeline error: ${msg}`)
      }
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      <div className="noise-overlay" aria-hidden="true" />

      <AnimatePresence>
        {loading && <LoadingOverlay activeModule={activeModule} />}
      </AnimatePresence>

      {/* Navbar */}
      <motion.header
        initial={{ y: -60, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] max-w-3xl"
      >
        <nav className="flex items-center justify-between px-4 py-3 rounded-full bg-zinc-900/40 backdrop-blur-md border border-zinc-800">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
              <span className="text-zinc-950 font-bold text-sm">C</span>
            </div>
            <span className="font-semibold text-white hidden sm:block">CADIS</span>
          </Link>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800">
              <span className="w-2 h-2 rounded-full bg-emerald-500 pulse-glow" />
              <span className="text-xs text-zinc-400">Pipeline Ready</span>
            </div>
          </div>
        </nav>
      </motion.header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pt-24 pb-16">
        <div className="w-full max-w-2xl">

          {/* Heading */}
          <div className="text-center mb-10">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800 mb-6 text-xs text-zinc-500 font-mono"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Research Platform v2.0
            </motion.div>

            <h1
              className="text-4xl sm:text-5xl font-bold tracking-tight text-white mb-4 overflow-hidden"
              style={{ fontFamily: "var(--font-cal-sans), sans-serif" }}
            >
              <span className="block overflow-hidden">
                <motion.span className="block" variants={textRevealVariants} initial="hidden" animate="visible" custom={0}>
                  Welcome to CADIS
                </motion.span>
              </span>
            </h1>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="text-zinc-400 text-base max-w-md mx-auto"
            >
              Upload a document or paste text to run the full 6-module NLP pipeline.
            </motion.p>
          </div>

          {/* Error banner */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="flex items-start gap-3 p-4 mb-6 rounded-2xl bg-red-950/40 border border-red-900/60 text-red-400 text-sm font-mono"
              >
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Mode toggle */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="flex items-center justify-center mb-6"
          >
            <div className="inline-flex items-center p-1 rounded-full bg-zinc-900 border border-zinc-800">
              {(["upload", "paste", "sample"] as const).map((m) => (
                <button key={m} onClick={() => setMode(m)}
                  className={`relative px-4 py-1.5 text-sm font-medium rounded-full transition-colors ${mode === m ? "text-white" : "text-zinc-400"}`}>
                  {mode === m && (
                    <motion.div layoutId="mode-toggle" className="absolute inset-0 bg-zinc-800 rounded-full"
                      transition={{ type: "spring", stiffness: 500, damping: 30 }} />
                  )}
                  <span className="relative z-10 flex items-center gap-1.5">
                    {m === "upload" && <><Upload className="w-3.5 h-3.5" /> Upload File</>}
                    {m === "paste"  && <><FileText className="w-3.5 h-3.5" /> Paste Text</>}
                    {m === "sample" && <><Sparkles className="w-3.5 h-3.5" /> Try a Sample</>}
                  </span>
                </button>
              ))}
            </div>
          </motion.div>

          {/* Upload / Paste */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.6 }}>
            <AnimatePresence mode="wait">
              {mode === "sample" ? (
                <motion.div key="sample" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {SAMPLES.map((s) => {
                      const active = selectedSample === s.id
                      return (
                        <button key={s.id} onClick={() => loadSample(s.id)}
                          className={`text-left p-4 rounded-2xl border transition-all duration-200 ${
                            active
                              ? "bg-zinc-800 border-zinc-600"
                              : "bg-zinc-900/50 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900"
                          }`}>
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`px-2 py-0.5 rounded-full border text-xs font-mono font-semibold ${s.tagColor}`}>{s.tag}</span>
                            {active && <span className="text-xs text-emerald-400 font-mono">✓ selected</span>}
                          </div>
                          <p className="text-white text-sm font-semibold mb-1">{s.label}</p>
                          <p className="text-zinc-500 text-xs leading-relaxed line-clamp-2">{s.preview}</p>
                          <p className="text-zinc-700 text-xs font-mono mt-2">{s.text.split(" ").length} words</p>
                        </button>
                      )
                    })}
                  </div>
                  {selectedSample && (
                    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
                      className="mt-4 p-4 rounded-xl bg-zinc-900/60 border border-zinc-800 max-h-32 overflow-y-auto">
                      <p className="text-zinc-400 text-xs font-mono leading-relaxed">
                        {SAMPLES.find(s => s.id === selectedSample)?.text.slice(0, 300)}…
                      </p>
                    </motion.div>
                  )}
                </motion.div>
              ) : mode === "upload" ? (
                <motion.div key="upload" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}>
                  {!file ? (
                    <div
                      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                      onDragLeave={() => setDragging(false)}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                      className={`relative flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-300 p-16 ${
                        dragging ? "border-zinc-500 bg-zinc-800/30" : "border-zinc-800 bg-zinc-900/30 hover:border-zinc-600 hover:bg-zinc-900/50"
                      }`}
                    >
                      <motion.div animate={dragging ? { scale: 1.1 } : { scale: 1 }} className="p-4 rounded-2xl bg-zinc-800">
                        <Upload className="w-8 h-8 text-zinc-400" strokeWidth={1.5} />
                      </motion.div>
                      <div className="text-center">
                        <p className="text-white font-medium mb-1">Drop your document here</p>
                        <p className="text-zinc-500 text-sm">or click to browse</p>
                        <div className="flex items-center justify-center gap-2 mt-2">
                          {[".txt", ".pdf", ".docx"].map(ext => (
                            <span key={ext} className="px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-500 text-xs font-mono">{ext}</span>
                          ))}
                        </div>
                      </div>
                      <input ref={fileInputRef} type="file" accept=".txt,.pdf,.docx" className="hidden" onChange={handleFileChange} />
                    </div>
                  ) : (
                    <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
                      className="flex items-center gap-4 p-5 rounded-2xl bg-zinc-900 border border-zinc-800">
                      <div className="p-3 rounded-xl bg-zinc-800"><FileText className="w-6 h-6 text-white" strokeWidth={1.5} /></div>
                      <div className="flex-1 min-w-0">
                        <p className="text-white font-medium truncate">{file.name}</p>
                        {fileContent
                          ? <p className="text-zinc-500 text-sm">{(file.size / 1024).toFixed(1)} KB · {fileContent.split(/\s+/).filter(Boolean).length} words extracted</p>
                          : <p className="text-zinc-500 text-sm flex items-center gap-1.5">
                              <span className="w-2.5 h-2.5 border border-zinc-600 border-t-zinc-300 rounded-full animate-spin inline-block" />
                              Extracting text…
                            </p>
                        }
                      </div>
                      <button onClick={() => { setFile(null); setFileContent("") }}
                        className="p-2 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors">
                        <X className="w-4 h-4" />
                      </button>
                    </motion.div>
                  )}
                </motion.div>
              ) : (
                <motion.div key="paste" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.25 }}>
                  <div className="relative rounded-2xl bg-zinc-900 border border-zinc-800 focus-within:border-zinc-600 transition-colors">
                    <textarea
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      placeholder="Paste your document text here…"
                      rows={10}
                      className="w-full bg-transparent text-white placeholder-zinc-600 text-sm p-5 resize-none outline-none rounded-2xl font-mono leading-relaxed"
                    />
                    {text && (
                      <button onClick={() => setText("")}
                        className="absolute top-3 right-3 p-1.5 rounded-lg text-zinc-600 hover:text-white hover:bg-zinc-800 transition-colors">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <div className="px-5 pb-3 flex items-center justify-between">
                      <span className="text-xs text-zinc-600 font-mono">{text.split(/\s+/).filter(Boolean).length} words</span>
                      {text.trim().length > 0 && text.trim().length <= 20 && (
                        <span className="text-xs text-amber-500">Add more text to proceed</span>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Pipeline breadcrumb */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.8 }}
            className="flex flex-wrap items-center justify-center gap-2 mt-6 mb-8">
            {MODULES.map((mod, i) => (
              <span key={mod.label} className="flex items-center gap-1.5 text-xs text-zinc-600 font-mono">
                {mod.label}
                {i < MODULES.length - 1 && <ChevronRight className="w-3 h-3 text-zinc-800" />}
              </span>
            ))}
          </motion.div>

          {/* Run button */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.9 }}>
            <Button
              size="lg"
              disabled={!ready || loading}
              onClick={handleRun}
              className={`w-full h-12 rounded-full text-base font-medium transition-all duration-300 ${
                ready && !loading
                  ? "shimmer-btn bg-white text-zinc-950 hover:bg-zinc-200 shadow-lg shadow-white/10"
                  : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
              }`}
            >
              {loading ? "Running Pipeline…" : "Run CADIS Pipeline"}
              {!loading && <ArrowRight className="ml-2 w-4 h-4" />}
            </Button>
            <p className="text-center text-xs text-zinc-600 mt-3 font-mono">
              {loading
                ? "Processing with real ML models — this takes ~30s"
                : ready
                ? "Pipeline ready — click to analyze"
                : mode === "sample"
                ? "Select a sample document above to begin"
                : "Upload a file or paste text to begin"}
            </p>
          </motion.div>
        </div>
      </main>
    </div>
  )
}
