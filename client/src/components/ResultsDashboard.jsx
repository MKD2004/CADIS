import { useState, useRef, useEffect } from "react";
import { AnimatePresence } from "framer-motion";
import { motion } from "motion/react";
import {
  FileText, Tag, Database, RotateCcw, ChevronDown,
  ChevronUp, Copy, Check, Layers, Clock, Hash,
  AlertTriangle, CheckCircle2, Info,
  MessageSquare, Send, User, Bot, Loader2, Zap,
} from "lucide-react";
import { chat } from "@/lib/api";
import BorderGlow from "@/components/BorderGlow";
import CountUp from "@/components/CountUp";

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

const ENTITY_COLORS = {
  PERSON:       "text-[#60a5fa] bg-[#60a5fa]/10 border-[#60a5fa]/30",
  COMPANY:      "text-[#a78bfa] bg-[#a78bfa]/10 border-[#a78bfa]/30",
  ORGANIZATION: "text-[#a78bfa] bg-[#a78bfa]/10 border-[#a78bfa]/30",
  LOCATION:     "text-[#34d399] bg-[#34d399]/10 border-[#34d399]/30",
  DATE:         "text-[#22d3ee] bg-[#22d3ee]/10 border-[#22d3ee]/30",
  MONEY:        "text-[#fbbf24] bg-[#fbbf24]/10 border-[#fbbf24]/30",
  "THREAT ACTOR": "text-[#f472b6] bg-[#f472b6]/10 border-[#f472b6]/30",
  MALWARE:      "text-[#f87171] bg-[#f87171]/10 border-[#f87171]/30",
  VULNERABILITY:"text-[#fb923c] bg-[#fb923c]/10 border-[#fb923c]/30",
  "IP ADDRESS": "text-[#22d3ee] bg-[#22d3ee]/10 border-[#22d3ee]/30",
};

function getEntityColor(label) {
  return ENTITY_COLORS[label?.toUpperCase()] || "text-[#a78bfa] bg-[#a78bfa]/10 border-[#a78bfa]/30";
}

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); } catch {}
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={copy} className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors">
      {copied ? <Check className="h-3.5 w-3.5 text-[#34d399]" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

function SectionLabel({ icon: Icon, label, accent = "text-primary", children }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <Icon className={`h-3.5 w-3.5 ${accent}`} />
        <span className="font-mono text-[10px] uppercase tracking-widest text-white/40">{label}</span>
      </div>
      {children}
    </div>
  );
}

function Stat({ label, value, color = "text-primary" }) {
  return (
    <div>
      <div className="font-mono text-[10px] tracking-widest text-white/30 uppercase">{label}</div>
      <div className={`mt-1 font-display text-2xl font-extrabold ${color}`}>
        {typeof value === "number" ? <CountUp from={0} to={value} duration={1.2} separator="," /> : value ?? "—"}
      </div>
    </div>
  );
}

function LatencyTag({ ms }) {
  if (!ms) return null;
  return (
    <span className="inline-flex items-center gap-1 font-mono text-[10px] text-primary/70 bg-primary/10 px-1.5 py-0.5 rounded-full">
      <Zap className="h-2.5 w-2.5" />
      {Math.round(ms)}ms
    </span>
  );
}

// ── Summary Card ──────────────────────────────────────────────
function SummaryCard({ data }) {
  const summary = data?.executive_summary
    || (data?.enriched_text ? data.enriched_text.slice(0, 600) + "…" : null)
    || "No summary available.";

  return (
    <motion.div variants={cardVariants}>
      <BorderGlow>
        <div className="p-5 flex flex-col gap-4 min-h-[320px]">
          <SectionLabel icon={FileText} label="Executive Summary">
            <div className="flex items-center gap-2">
              <LatencyTag ms={data?.latency_ms?.distilbart} />
              <CopyBtn text={summary} />
            </div>
          </SectionLabel>
          <p className="text-[14px] text-white/70 leading-relaxed flex-1">{summary}</p>
        </div>
      </BorderGlow>
    </motion.div>
  );
}

// ── Entities Card ─────────────────────────────────────────────
function EntitiesCard({ data }) {
  const [filter, setFilter] = useState("ALL");
  const entities = data?.document_entities || {};

  const flat = Object.entries(entities).flatMap(([label, arr]) =>
    (Array.isArray(arr) ? arr : []).map((e) => ({
      ...e,
      label: (e.label || label).toUpperCase(),
    }))
  );

  const labels = ["ALL", ...Object.keys(entities).map((l) => l.toUpperCase())];
  const filtered = filter === "ALL" ? flat : flat.filter((e) => e.label === filter);

  return (
    <motion.div variants={cardVariants}>
      <BorderGlow>
        <div className="p-5 flex flex-col gap-4">
          <SectionLabel icon={Tag} label="Extracted Entities" accent="text-[#a78bfa]">
            <div className="flex items-center gap-2">
              <LatencyTag ms={data?.latency_ms?.gliner} />
              <span className="font-mono text-[10px] text-white/30">{flat.length} total</span>
            </div>
          </SectionLabel>

          <div className="flex flex-wrap gap-1.5">
            {labels.map((lbl) => (
              <button
                key={lbl}
                onClick={() => setFilter(lbl)}
                className={`font-mono text-[10px] tracking-wider px-2.5 py-1 rounded-lg border transition-all ${
                  filter === lbl
                    ? "bg-primary/15 border-primary/30 text-primary"
                    : "border-white/[0.06] text-white/30 hover:text-white/50 hover:border-white/10"
                }`}
              >
                {lbl}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto no-scrollbar content-start">
            {filtered.length > 0 ? filtered.map((e, i) => (
              <span
                key={`${e.text}-${i}`}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[12px] font-mono ${getEntityColor(e.label)}`}
              >
                {e.text}
                {e.score !== undefined && (
                  <span className="opacity-50 text-[9px]">{(e.score * 100).toFixed(0)}%</span>
                )}
              </span>
            )) : (
              <p className="font-mono text-xs text-white/30 py-4">No entities for this label.</p>
            )}
          </div>
        </div>
      </BorderGlow>
    </motion.div>
  );
}

// ── Metadata Card ─────────────────────────────────────────────
function MetadataCard({ data, fileName }) {
  const meta = data?.metadata || {};
  const chunks = meta?.chunks_stored;
  const pages = data?.total_pages;
  const entityCount = Object.values(data?.document_entities || {}).reduce((a, arr) => a + (arr?.length || 0), 0);
  const ambiguities = data?.pipeline_flags?.ambiguities_found ?? 0;

  return (
    <motion.div variants={cardVariants}>
      <BorderGlow>
        <div className="p-5 flex flex-col gap-5">
          <SectionLabel icon={Database} label="Document Metadata" accent="text-[#22d3ee]" />

          {fileName && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.06]">
              <FileText className="h-3 w-3 text-primary flex-shrink-0" />
              <span className="font-mono text-xs text-white/60 truncate">{fileName}</span>
              {data?.pipeline_flags?.is_sample && (
                <span className="font-mono text-[9px] tracking-wider text-primary bg-primary/10 px-1.5 py-0.5 rounded-full uppercase">Sample</span>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <Stat label="Pages" value={pages} color="text-[#22d3ee]" />
            <Stat label="Chunks" value={chunks} color="text-[#a78bfa]" />
            <Stat label="Entities" value={entityCount} color="text-[#60a5fa]" />
            <Stat label="Ambiguities" value={ambiguities} color="text-[#fbbf24]" />
          </div>

          <div className="border-t border-white/[0.06] pt-4 space-y-2">
            <span className="font-mono text-[10px] text-white/30 uppercase tracking-widest">Pipeline Flags</span>
            {[
              { label: "VLM Ran", value: meta?.vlm_ran, icon: CheckCircle2 },
              { label: "Strategy", value: meta?.strategy, icon: Info },
              { label: "Collection", value: meta?.collection, icon: Layers },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className="h-3 w-3 text-white/20" />
                  <span className="font-mono text-[10px] text-white/30 tracking-wider uppercase">{label}</span>
                </div>
                <span className="font-mono text-[10px] text-white/50">
                  {value === true ? "✓ Yes" : value === false ? "✗ No" : value ?? "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </BorderGlow>
    </motion.div>
  );
}

// ── JSON Viewer ───────────────────────────────────────────────
function JsonViewer({ data }) {
  const [expanded, setExpanded] = useState(false);
  const json = JSON.stringify(data, null, 2);

  return (
    <motion.div variants={cardVariants}>
      <BorderGlow>
        <div className="overflow-hidden">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-2">
              <Hash className="h-3.5 w-3.5 text-white/30" />
              <span className="font-mono text-[10px] uppercase tracking-widest text-white/40">Raw JSON Response</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-white/20">
                {(new TextEncoder().encode(json).length / 1024).toFixed(1)} KB
              </span>
              {expanded ? <ChevronUp className="h-3.5 w-3.5 text-white/30" /> : <ChevronDown className="h-3.5 w-3.5 text-white/30" />}
            </div>
          </button>
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: "auto" }}
                exit={{ height: 0 }}
                className="overflow-hidden"
              >
                <div className="border-t border-white/[0.06]">
                  <div className="flex justify-end px-4 py-2 bg-white/[0.01]">
                    <CopyBtn text={json} />
                  </div>
                  <pre className="px-5 pb-5 font-mono text-[10px] text-white/40 leading-relaxed overflow-x-auto max-h-80 no-scrollbar">
                    {json}
                  </pre>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </BorderGlow>
    </motion.div>
  );
}

// ── Chat Card ─────────────────────────────────────────────────
function ChatCard({ documentId, isSample }) {
  const [messages, setMessages] = useState([
    {
      role: "bot",
      content: isSample
        ? "This is a pre-loaded sample document. Try asking: \"What is this document about?\""
        : "Neural chat initialized. Ask me anything about the extracted document.",
    },
  ]);
  const [input, setInput] = useState(isSample ? "What is this document about?" : "");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isTyping) return;

    const userText = input;
    setMessages((prev) => [...prev, { role: "user", content: userText }]);
    setInput("");
    setIsTyping(true);

    try {
      const res = await chat(userText, documentId || "current");
      const latency = res.latency_ms || {};
      const totalMs = (latency.minilm || 0) + (latency.roberta || 0);
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          content: res.answer || "No response received.",
          latencyMs: totalMs || null,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "bot", content: "Error: Could not connect to the neural backend." },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <motion.div variants={cardVariants}>
      <BorderGlow>
        <div className="p-5 flex flex-col h-[420px]">
          <SectionLabel icon={MessageSquare} label="Interactive Document Q&A" />

          <div ref={scrollRef} className="flex-1 overflow-y-auto no-scrollbar flex flex-col gap-3 mb-4 pt-2">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 border ${
                    msg.role === "user"
                      ? "bg-primary/15 text-primary border-primary/30"
                      : "bg-[#a78bfa]/15 text-[#a78bfa] border-[#a78bfa]/30"
                  }`}
                >
                  {msg.role === "user" ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                </div>
                <div
                  className={`px-4 py-2.5 rounded-xl text-sm leading-relaxed max-w-[80%] ${
                    msg.role === "user"
                      ? "bg-primary/10 border border-primary/20 text-white/90 rounded-tr-none"
                      : "bg-white/[0.03] border border-white/[0.06] text-white/70 rounded-tl-none"
                  }`}
                >
                  {msg.content}
                  {msg.latencyMs > 0 && (
                    <span className="ml-2"><LatencyTag ms={msg.latencyMs} /></span>
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-[#a78bfa]/15 text-[#a78bfa] border border-[#a78bfa]/30">
                  <Bot className="h-3.5 w-3.5" />
                </div>
                <div className="px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center gap-2 rounded-tl-none">
                  <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
                  <span className="font-mono text-[10px] text-white/30 uppercase tracking-widest">Querying vector space…</span>
                </div>
              </div>
            )}
          </div>

          <form onSubmit={handleSend} className="relative flex items-center mt-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about this document…"
              className="w-full bg-white/[0.02] border border-white/[0.06] rounded-xl py-3 pl-4 pr-12 text-sm text-white/90 placeholder-white/30 focus:outline-none focus:border-primary/40 transition-all"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="absolute right-2 p-2 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-30 transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </BorderGlow>
    </motion.div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────
export default function ResultsDashboard({ data, fileName, onReset }) {
  return (
    <div className="px-4 py-8 md:px-8">
      {/* Header */}
      <motion.div
        className="max-w-6xl mx-auto flex items-center justify-between mb-8"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-[#34d399] animate-pulse" />
            <span className="font-mono text-[10px] tracking-widest text-[#34d399] uppercase">
              Analysis Complete
            </span>
          </div>
          <h2 className="font-display text-2xl font-extrabold text-white">
            CADIS Results
          </h2>
        </div>

        <button
          onClick={onReset}
          className="
            cursor-target flex items-center gap-2 px-4 py-2 rounded-xl
            border border-white/[0.06] hover:border-primary/30
            text-sm text-white/50 hover:text-primary
            transition-all duration-200
          "
        >
          <RotateCcw className="h-3.5 w-3.5" />
          New Document
        </button>
      </motion.div>

      {/* Bento grid */}
      <motion.div
        className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 items-start"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <div className="lg:col-span-1 lg:row-span-2">
          <SummaryCard data={data} />
        </div>
        <div className="lg:col-span-1">
          <EntitiesCard data={data} />
        </div>
        <div className="lg:col-span-1">
          <MetadataCard data={data} fileName={fileName} />
        </div>
        <div className="md:col-span-2 lg:col-span-2">
          <JsonViewer data={data} />
        </div>
        <div className="md:col-span-2 lg:col-span-3 mt-2">
          <ChatCard documentId={data?.document_id} isSample={data?.pipeline_flags?.is_sample} />
        </div>
      </motion.div>
    </div>
  );
}
