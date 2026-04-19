import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, Cpu, CheckCircle2, Circle, Loader } from "lucide-react";

// ── Pipeline module definitions ────────────────────────────────
const PIPELINE_MODULES = [
  {
    id: "preprocessing",
    label: "NLP Preprocessing Engine",
    tag: "MOD-01",
    color: "text-signal-400",
    border: "border-signal-500/30",
    bg: "bg-signal-500/5",
    glow: "rgba(6,182,212,0.15)",
    logs: [
      "→ Initializing spaCy pipeline (en_core_web_sm)...",
      "→ Running tokenization pass...",
      "→ POS tagging: NOUN, VERB, ADJ, PROPN detected",
      "→ Lemmatization complete. Stopword filter applied.",
      "✓ Token stream extracted. 847 tokens / 34 sentences",
    ],
    duration: 1600,
  },
  {
    id: "embeddings",
    label: "Semantic Embedding Module",
    tag: "MOD-02",
    color: "text-neural-400",
    border: "border-neural-500/30",
    bg: "bg-neural-500/5",
    glow: "rgba(139,92,246,0.15)",
    logs: [
      "→ Loading all-MiniLM-L6-v2 (sentence-transformers)...",
      "→ Encoding 34 sentence windows → 384-dim vectors",
      "→ Computing cosine similarity matrix [34×34]...",
      "→ Semantic clusters identified: 4 topic groups",
      "✓ Embedding space constructed. Mean similarity: 0.412",
    ],
    duration: 1800,
  },
  {
    id: "ner",
    label: "GliNER Zero-Shot NER",
    tag: "MOD-03",
    color: "text-data-400",
    border: "border-data-500/30",
    bg: "bg-data-500/5",
    glow: "rgba(251,191,36,0.12)",
    logs: [
      "→ Loading urchade/gliner_base model...",
      "→ Running zero-shot NER (threshold=0.50, flat_ner=True)...",
      "→ Entity scan: PERSON, ORG, LOCATION, DATE, MONEY...",
      "→ Relation extraction: SVO triples → 12 relations found",
      "✓ 31 entities extracted. Structured JSON serialized.",
    ],
    duration: 2000,
  },
  {
    id: "ambiguity",
    label: "Ambiguity Detection Layer",
    tag: "MOD-04",
    color: "text-red-400",
    border: "border-red-500/30",
    bg: "bg-red-500/5",
    glow: "rgba(239,68,68,0.12)",
    logs: [
      "→ Scanning dependency parse trees for PP attachments...",
      "→ Pronoun resolution: anaphora chain analysis...",
      '→ Ambiguity: "she" → candidate antecedents [CFO, Commission]',
      "→ Resolving via contextual embedding cosine distance...",
      "✓ 3 ambiguities detected. 3/3 resolved (conf ≥ 0.71)",
    ],
    duration: 1700,
  },
  {
    id: "qa",
    label: "Extractive QA Engine",
    tag: "MOD-05",
    color: "text-pulse-400",
    border: "border-pulse-400/30",
    bg: "bg-pulse-400/5",
    glow: "rgba(52,211,153,0.12)",
    logs: [
      "→ Loading deepset/minilm-uncased-squad2...",
      "→ Generating 7 auto-questions from entity types...",
      '→ Q: "Who confirmed the deal?" → A: "Tim Cook" (0.91)',
      '→ Q: "Where was the conference?" → A: "San Francisco" (0.88)',
      "✓ QA engine complete. 7/7 questions answered.",
    ],
    duration: 1900,
  },
  {
    id: "summary",
    label: "Intelligent Summary Generator",
    tag: "MOD-06",
    color: "text-violet-400",
    border: "border-violet-500/30",
    bg: "bg-violet-500/5",
    glow: "rgba(167,139,250,0.15)",
    logs: [
      "→ Loading sshleifer/distilbart-cnn-12-6...",
      "→ Chunking enriched text (400-token windows)...",
      "→ Running abstractive summarization pass...",
      "→ Extracting 4 key sentences by entity density...",
      "✓ Executive summary generated. Compression: 84%",
    ],
    duration: 2200,
  },
];

// ── Individual log line ────────────────────────────────────────
function LogLine({ text, delay, moduleColor }) {
  // Add this safety catch to prevent the StrictMode crash!
  if (!text) return null; 

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay }}
      className={`font-mono text-xs leading-relaxed ${
        text.startsWith("✓")
          ? "text-pulse-400 font-500"
          : "text-slate-500"
      }`}
    >
      {text}
    </motion.div>
  );
}

// ── Module row ─────────────────────────────────────────────────
function ModuleRow({ module, state, startDelay }) {
  // state: "pending" | "running" | "done"
  const [visibleLogs, setVisibleLogs] = useState([]);
  const isRunning = state === "running";
  const isDone    = state === "done";

  // Stream log lines while running
  useEffect(() => {
    if (!isRunning && !isDone) { setVisibleLogs([]); return; }
    if (isDone) { setVisibleLogs(module.logs); return; }

    let idx = 0;
    const iv = setInterval(() => {
      if (idx < module.logs.length) {
        setVisibleLogs((prev) => [...prev, module.logs[idx]]);
        idx++;
      } else {
        clearInterval(iv);
      }
    }, module.duration / module.logs.length);
    return () => clearInterval(iv);
  }, [isRunning, isDone]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: startDelay, ease: [0.22, 1, 0.36, 1] }}
    >
      <div
        className={`
          rounded-xl border overflow-hidden transition-all duration-500
          ${isDone    ? `${module.border} ${module.bg}` : "border-glass"}
          ${isRunning ? `${module.border} ${module.bg}` : ""}
        `}
        style={{
          boxShadow: (isRunning || isDone)
            ? `0 0 20px ${module.glow}, inset 0 0 20px ${module.glow}`
            : "none",
          transition: "box-shadow 0.5s ease",
        }}
      >
        {/* Module header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-glass">
          <div className="flex items-center gap-3">
            {/* Status icon */}
            <div className="w-4 h-4 flex items-center justify-center flex-shrink-0">
              {isDone ? (
                <motion.div
                  initial={{ scale: 0, rotate: -90 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 20 }}
                >
                  <CheckCircle2 size={14} className={module.color} />
                </motion.div>
              ) : isRunning ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <Loader size={14} className={module.color} />
                </motion.div>
              ) : (
                <Circle size={14} className="text-slate-700" />
              )}
            </div>

            {/* Label */}
            <span className={`font-display text-sm font-500 transition-colors duration-300 ${
              isRunning || isDone ? "text-slate-200" : "text-slate-600"
            }`}>
              {module.label}
            </span>
          </div>

          {/* Tag */}
          <span className={`font-mono text-[10px] tracking-widest transition-colors duration-300 ${
            isRunning || isDone ? module.color : "text-slate-700"
          }`}>
            {module.tag}
          </span>
        </div>

        {/* Log output */}
        <AnimatePresence>
          {(isRunning || isDone) && visibleLogs.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="px-4 py-3 space-y-1 overflow-hidden"
            >
              {visibleLogs.map((log, i) => (
                <LogLine
                  key={i}
                  text={log}
                  delay={0}
                  moduleColor={module.color}
                />
              ))}
              {/* Cursor on last line if running */}
              {isRunning && (
                <motion.span
                  className={`font-mono text-xs ${module.color}`}
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                >
                  █
                </motion.span>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ── Main terminal ──────────────────────────────────────────────
export default function ProcessingTerminal({ fileName }) {
  // Track which module is active
  const [activeIndex, setActiveIndex] = useState(0);
  const [completedCount, setCompletedCount] = useState(0);
  const [globalDone, setGlobalDone] = useState(false);
  const timerRef = useRef(null);

  const getModuleState = (i) => {
    if (i < completedCount) return "done";
    if (i === activeIndex && !globalDone) return "running";
    return "pending";
  };

  // Advance through modules
  useEffect(() => {
    const advance = (idx) => {
      if (idx >= PIPELINE_MODULES.length) {
        setGlobalDone(true);
        return;
      }
      setActiveIndex(idx);
      timerRef.current = setTimeout(() => {
        setCompletedCount(idx + 1);
        advance(idx + 1);
      }, PIPELINE_MODULES[idx].duration);
    };

    const init = setTimeout(() => advance(0), 600);
    return () => { clearTimeout(init); clearTimeout(timerRef.current); };
  }, []);

  const progress = Math.round((completedCount / PIPELINE_MODULES.length) * 100);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      {/* Terminal window */}
      <motion.div
        className="w-full max-w-2xl"
        initial={{ opacity: 0, scale: 0.97, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* Window chrome */}
        <div className="glass-bright rounded-2xl overflow-hidden shadow-glass-lg border border-glass-bright">
          {/* Title bar */}
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-glass bg-slate-950/60">
            <div className="flex items-center gap-2">
              {/* Traffic lights */}
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500/70" />
                <div className="w-3 h-3 rounded-full bg-data-400/70" />
                <div className="w-3 h-3 rounded-full bg-pulse-500/70" />
              </div>
              <div className="flex items-center gap-2 ml-3">
                <Terminal size={12} className="text-signal-500" />
                <span className="font-mono text-xs text-slate-500 tracking-wider">
                  cadis · neural-pipeline
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Cpu size={11} className="text-signal-500" />
              <span className="font-mono text-[10px] text-signal-500 tracking-widest uppercase">
                Processing
              </span>
              <motion.span
                className="font-mono text-[10px] text-signal-400"
                animate={{ opacity: [1, 0, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              >
                ●
              </motion.span>
            </div>
          </div>

          {/* File banner */}
          {fileName && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              transition={{ delay: 0.3 }}
              className="px-5 py-2.5 bg-signal-900/20 border-b border-signal-500/10"
            >
              <p className="font-mono text-[11px] text-signal-500/80 tracking-wider">
                <span className="text-signal-600">TARGET</span> /{fileName}
              </p>
            </motion.div>
          )}

          {/* Module list */}
          <div className="p-4 space-y-2.5 max-h-[calc(100vh-280px)] overflow-y-auto no-scrollbar">
            {PIPELINE_MODULES.map((mod, i) => (
              <ModuleRow
                key={mod.id}
                module={mod}
                state={getModuleState(i)}
                startDelay={i * 0.06}
              />
            ))}
          </div>

          {/* Progress footer */}
          <div className="px-5 py-4 border-t border-glass bg-slate-950/40">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs text-slate-600">
                {globalDone
                  ? "Pipeline complete"
                  : `Running module ${Math.min(activeIndex + 1, PIPELINE_MODULES.length)} of ${PIPELINE_MODULES.length}`}
              </span>
              <span className={`font-mono text-xs font-500 ${globalDone ? "text-pulse-400" : "text-signal-400"}`}>
                {progress}%
              </span>
            </div>

            {/* Progress bar */}
            <div className="relative h-1 bg-slate-800 rounded-full overflow-hidden">
              <motion.div
                className="absolute inset-y-0 left-0 rounded-full"
                style={{
                  background: globalDone
                    ? "linear-gradient(90deg, #10b981, #34d399)"
                    : "linear-gradient(90deg, #06b6d4, #8b5cf6)",
                }}
                initial={{ width: "0%" }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
              {/* Shimmer */}
              {!globalDone && (
                <motion.div
                  className="absolute inset-y-0 w-12 bg-gradient-to-r from-transparent via-white/10 to-transparent"
                  animate={{ x: [-48, 600] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Status message below terminal */}
        <motion.p
          className="text-center font-mono text-xs text-slate-600 tracking-widest mt-4 uppercase"
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          {globalDone ? "✓ Analysis complete · Loading results..." : "Neural inference in progress · Do not close tab"}
        </motion.p>
      </motion.div>
    </div>
  );
}
