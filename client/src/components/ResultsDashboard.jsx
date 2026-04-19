import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import {
  FileText, Tag, Database, RotateCcw, ChevronDown,
  ChevronUp, Copy, Check, Layers, Clock, Hash,
  TrendingUp, AlertTriangle, CheckCircle2, Info,
  MessageSquare, Send, User, Bot, Loader2,
} from "lucide-react";

// ── Animation variants ─────────────────────────────────────────
const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.07, delayChildren: 0.1 },
  },
};

const cardVariants = {
  hidden:  { opacity: 0, y: 28, filter: "blur(6px)" },
  visible: {
    opacity: 1, y: 0, filter: "blur(0px)",
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
  },
};

// ── Entity label → style mapping ───────────────────────────────
const ENTITY_STYLES = {
  PERSON:       { bg: "bg-data-400/10",   border: "border-data-400/30",   text: "text-data-300",   dot: "bg-data-400" },
  ORGANIZATION: { bg: "bg-neural-500/10", border: "border-neural-400/30", text: "text-neural-300", dot: "bg-neural-400" },
  LOCATION:     { bg: "bg-pulse-400/10",  border: "border-pulse-400/30",  text: "text-pulse-400",  dot: "bg-pulse-400" },
  DATE:         { bg: "bg-signal-500/10", border: "border-signal-400/30", text: "text-signal-300", dot: "bg-signal-400" },
  MONEY:        { bg: "bg-signal-500/10", border: "border-signal-400/30", text: "text-signal-300", dot: "bg-signal-400" },
  MISC:         { bg: "bg-slate-700/20",  border: "border-slate-600/30",  text: "text-slate-400",  dot: "bg-slate-500" },
  default:      { bg: "bg-violet-500/10", border: "border-violet-400/30", text: "text-violet-300", dot: "bg-violet-400" },
};

function entityStyle(label) {
  return ENTITY_STYLES[label?.toUpperCase()] || ENTITY_STYLES.default;
}

// ── Copy button ────────────────────────────────────────────────
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(text); } catch {}
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="p-1.5 rounded-lg hover:bg-slate-800/60 text-slate-600 hover:text-slate-300 transition-colors"
    >
      {copied ? <Check size={13} className="text-pulse-400" /> : <Copy size={13} />}
    </button>
  );
}

// ── Section header ─────────────────────────────────────────────
function CardHeader({ icon: Icon, label, accent = "text-slate-500", children }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <Icon size={14} className={accent} />
        <span className="label">{label}</span>
      </div>
      {children}
    </div>
  );
}

// ── Stat cell ──────────────────────────────────────────────────
function StatCell({ label, value, accent }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[10px] text-slate-600 tracking-widest uppercase">{label}</span>
      <span className={`font-display text-2xl font-700 ${accent}`}>{value ?? "—"}</span>
    </div>
  );
}

// ── Entity pill ────────────────────────────────────────────────
function EntityPill({ entity }) {
  const s = entityStyle(entity.label);
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 350, damping: 25 }}
      className={`entity-pill ${s.bg} ${s.border} ${s.text} flex items-center gap-1.5`}
    >
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${s.dot}`} />
      <span className="truncate max-w-[120px]">{entity.text}</span>
      {entity.score !== undefined && (
        <span className="opacity-50 text-[9px] flex-shrink-0">
          {(entity.score * 100).toFixed(0)}%
        </span>
      )}
    </motion.div>
  );
}

// ── QA row ─────────────────────────────────────────────────────
function QARow({ qa, index }) {
  const conf = qa.confidence ?? qa.score ?? 0;
  const confColor =
    conf >= 0.7 ? "text-pulse-400" :
    conf >= 0.4 ? "text-data-400"  : "text-red-400";
  const barColor =
    conf >= 0.7 ? "bg-pulse-500" :
    conf >= 0.4 ? "bg-data-400"  : "bg-red-500";

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.06, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className="group rounded-xl border border-glass p-3 hover:border-glass-bright transition-colors duration-200"
    >
      <p className="font-mono text-[10px] text-slate-500 tracking-wider mb-1 uppercase">
        {qa.question}
      </p>
      <p className="font-display text-sm font-500 text-slate-200 mb-2 leading-snug">
        {qa.answer}
      </p>
      {/* Confidence bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-0.5 bg-slate-800 rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${barColor}`}
            initial={{ width: 0 }}
            animate={{ width: `${conf * 100}%` }}
            transition={{ duration: 0.6, delay: index * 0.06 + 0.2, ease: "easeOut" }}
          />
        </div>
        <span className={`font-mono text-[10px] ${confColor} flex-shrink-0`}>
          {(conf * 100).toFixed(0)}%
        </span>
      </div>
    </motion.div>
  );
}

// ── Relation row ───────────────────────────────────────────────
function RelationRow({ rel, index }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.05 }}
      className="flex items-center gap-2 py-1.5 border-b border-glass last:border-0"
    >
      <span className="font-mono text-xs text-data-400 font-500 truncate max-w-[90px]">
        {rel.Subject || rel.subject}
      </span>
      <span className="font-mono text-[10px] text-slate-600 px-1.5 py-0.5 rounded bg-slate-800/40 flex-shrink-0">
        {rel.Verb || rel.verb}
      </span>
      <span className="font-mono text-xs text-signal-400 font-500 truncate max-w-[90px]">
        {rel.Object || rel.object}
      </span>
    </motion.div>
  );
}

// ── BOX 1: Executive Summary ───────────────────────────────────
function SummaryCard({ data }) {
  const summary = data?.executive_summary 
    || data?.summary?.executive
    || (data?.enriched_text ? data.enriched_text.slice(0, 600) + "..." : null)
    || "No summary available in the response.";

  return (
    <motion.div
      variants={cardVariants}
      className="glass-bright rounded-2xl p-5 border border-glass-bright flex flex-col gap-4 row-span-2 shadow-glass"
    >
      {/* Top accent bar */}
      <div className="h-0.5 w-full rounded-full bg-gradient-data opacity-60" />

      <CardHeader icon={FileText} label="Executive Summary" accent="text-signal-400">
        <CopyButton text={summary} />
      </CardHeader>

      <div className="flex-1 overflow-y-auto no-scrollbar">
        <p className="font-body text-sm text-slate-300 leading-relaxed">
          {summary}
        </p>
      </div>

      {/* Key sentences */}
      {data?.key_sentences?.length > 0 && (
        <div className="border-t border-glass pt-4">
          <p className="label mb-3">Key Sentences</p>
          <div className="space-y-2">
            {data.key_sentences.slice(0, 3).map((s, i) => (
              <div key={i} className="flex gap-2">
                <div className="mt-2 w-1 h-1 rounded-full bg-neural-400 flex-shrink-0" />
                <p className="font-body text-xs text-slate-400 leading-relaxed">{s}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* QA Results */}
      {data?.qa_results?.length > 0 && (
        <div className="border-t border-glass pt-4">
          <p className="label mb-3">Auto QA</p>
          <div className="space-y-2">
            {data.qa_results.slice(0, 4).map((qa, i) => (
              <QARow key={i} qa={qa} index={i} />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ── BOX 2: Entities ────────────────────────────────────────────
function EntitiesCard({ data }) {
  const [activeFilter, setActiveFilter] = useState("ALL");
  const entities = data?.document_entities || data?.entities || {};

  // Flatten for display
  const allEntities = Object.entries(entities).flatMap(([label, arr]) =>
    (Array.isArray(arr) ? arr : []).map((e) => ({
      ...e,
      label: (e.label || label).toUpperCase(),
    }))
  );

  const labels = ["ALL", ...Object.keys(entities).map((l) => l.toUpperCase())];
  const filtered =
    activeFilter === "ALL"
      ? allEntities
      : allEntities.filter((e) => e.label === activeFilter);

  const relations = data?.relations || [];

  return (
    <motion.div
      variants={cardVariants}
      className="glass-bright rounded-2xl p-5 border border-glass-bright flex flex-col gap-4 shadow-glass"
    >
      <div className="h-0.5 w-full rounded-full bg-gradient-neural opacity-60" />

      <CardHeader icon={Tag} label="Extracted Entities" accent="text-neural-400">
        <span className="font-mono text-[10px] text-slate-600">
          {allEntities.length} total
        </span>
      </CardHeader>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-1.5">
        {labels.map((lbl) => {
          const s = entityStyle(lbl);
          const isActive = activeFilter === lbl;
          return (
            <button
              key={lbl}
              onClick={() => setActiveFilter(lbl)}
              className={`
                font-mono text-[10px] tracking-wider px-2.5 py-1 rounded-lg border transition-all duration-200
                ${isActive
                  ? `${s.bg} ${s.border} ${s.text}`
                  : "border-glass text-slate-600 hover:text-slate-400 hover:border-glass-bright"}
              `}
            >
              {lbl}
            </button>
          );
        })}
      </div>

      {/* Entity grid */}
      <div className="flex flex-wrap gap-1.5 flex-1 overflow-y-auto no-scrollbar content-start">
        <AnimatePresence mode="popLayout">
          {filtered.length > 0 ? (
            filtered.map((e, i) => <EntityPill key={`${e.text}-${i}`} entity={e} />)
          ) : (
            <motion.p
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="font-mono text-xs text-slate-600 py-4"
            >
              No entities for this label.
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Relation triples */}
      {relations.length > 0 && (
        <div className="border-t border-glass pt-4">
          <p className="label mb-3">SVO Relations</p>
          <div className="max-h-32 overflow-y-auto no-scrollbar">
            {relations.slice(0, 8).map((rel, i) => (
              <RelationRow key={i} rel={rel} index={i} />
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ── BOX 3: Document Metadata ───────────────────────────────────
function MetadataCard({ data, fileName }) {
  const meta   = data?.metadata || {};
  const stats  = data?.stats   || {};
  const chunks = meta?.chunks_stored || stats?.total_chunks;
  const pages  = data?.total_pages;
  const ents   = data?.stats?.total_entities
    || Object.values(data?.document_entities || {}).reduce((a, arr) => a + (arr?.length || 0), 0);
  const rels   = data?.stats?.total_relations || (data?.relations || []).length;

  const timeline  = data?.timeline || [];
  const ambiguities = data?.ambiguity_results || [];

  return (
    <motion.div
      variants={cardVariants}
      className="glass-bright rounded-2xl p-5 border border-glass-bright flex flex-col gap-5 shadow-glass"
    >
      <div className="h-0.5 w-full rounded-full bg-gradient-signal opacity-60" />

      <CardHeader icon={Database} label="Document Metadata" accent="text-signal-400" />

      {/* Filename */}
      {fileName && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/30 border border-glass">
          <FileText size={12} className="text-signal-500 flex-shrink-0" />
          <span className="font-mono text-xs text-slate-400 truncate">{fileName}</span>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-4">
        <StatCell label="Pages"       value={pages}  accent="text-signal-300" />
        <StatCell label="Chunks"      value={chunks} accent="text-neural-300" />
        <StatCell label="Entities"    value={ents}   accent="text-data-300" />
        <StatCell label="Relations"   value={rels}   accent="text-pulse-400" />
      </div>

      {/* Pipeline flags */}
      <div className="border-t border-glass pt-4 space-y-2">
        <p className="label mb-2">Pipeline Flags</p>
        {[
          { label: "VLM Ran",          value: meta?.vlm_ran,         icon: CheckCircle2 },
          { label: "Strategy",         value: meta?.strategy,        icon: Info },
          { label: "Collection",       value: meta?.collection,      icon: Layers },
          { label: "Ambiguities Found", value: data?.pipeline_flags?.ambiguities_found ?? "—", icon: AlertTriangle },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Icon size={11} className="text-slate-600" />
              <span className="font-mono text-[10px] text-slate-600 tracking-wider uppercase">{label}</span>
            </div>
            <span className="font-mono text-[10px] text-slate-400">
              {value === true  ? "✓ Yes" :
               value === false ? "✗ No"  :
               value ?? "—"}
            </span>
          </div>
        ))}
      </div>

      {/* Timeline */}
      {timeline.length > 0 && (
        <div className="border-t border-glass pt-4">
          <p className="label mb-3">Event Timeline</p>
          <div className="space-y-2">
            {timeline.slice(0, 4).map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.07 }}
                className="flex gap-3 items-start"
              >
                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-signal-500 flex-shrink-0" />
                <div>
                  <p className="font-mono text-[10px] text-signal-500">{item.time}</p>
                  <p className="font-body text-xs text-slate-500 leading-snug">{item.event}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ── Raw JSON Viewer ────────────────────────────────────────────
function JsonViewer({ data }) {
  const [expanded, setExpanded] = useState(false);
  const json = JSON.stringify(data, null, 2);

  return (
    <motion.div
      variants={cardVariants}
      className="glass rounded-2xl border border-glass overflow-hidden shadow-card"
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-slate-800/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Hash size={13} className="text-slate-600" />
          <span className="label">Raw JSON Response</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-slate-600">
            {(new TextEncoder().encode(json).length / 1024).toFixed(1)} KB
          </span>
          {expanded ? (
            <ChevronUp size={13} className="text-slate-600" />
          ) : (
            <ChevronDown size={13} className="text-slate-600" />
          )}
        </div>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="border-t border-glass">
              <div className="flex justify-end px-4 py-2 bg-slate-950/40">
                <CopyButton text={json} />
              </div>
              <pre className="px-5 pb-5 font-mono text-[10px] text-slate-500 leading-relaxed overflow-x-auto max-h-80 no-scrollbar">
                {json}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── BOX 5: RAG Chat Interface ──────────────────────────────────
function ChatCard({ fileName }) {
  const [messages, setMessages] = useState([
    { role: "bot", content: "Neural chat initialized. Ask me anything about the extracted document data." }
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!inputValue.trim()) return;

    const userText = inputValue;
    setMessages(prev => [...prev, { role: "user", content: userText }]);
    setInputValue("");
    setIsTyping(true);

    try {
      // Send query to the Node.js Gateway
      const res = await axios.post("http://localhost:5000/api/chat", {
        query: userText,
        document_id: fileName || "current"
      });
      
      setMessages(prev => [...prev, { 
        role: "bot", 
        content: res.data.answer || res.data.response || "No response received." 
      }]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: "bot", 
        content: "Error: Could not connect to the neural backend." 
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <motion.div
      variants={cardVariants}
      className="glass-bright rounded-2xl p-5 border border-glass-bright flex flex-col h-[450px] shadow-glass"
    >
      <div className="h-0.5 w-full rounded-full bg-gradient-signal opacity-60" />
      <CardHeader icon={MessageSquare} label="Interactive Document Q&A" accent="text-signal-400" />
      
      {/* Message History */}
      <div className="flex-1 overflow-y-auto no-scrollbar flex flex-col gap-4 mb-4 pt-2">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 border ${
                msg.role === "user" 
                  ? "bg-signal-500/20 text-signal-400 border-signal-500/30" 
                  : "bg-neural-500/20 text-neural-400 border-neural-500/30"
              }`}>
                {msg.role === "user" ? <User size={14} /> : <Bot size={14} />}
              </div>
              <div className={`px-4 py-2.5 rounded-xl text-sm leading-relaxed max-w-[80%] font-body ${
                msg.role === "user" 
                  ? "bg-signal-500/10 border border-signal-500/20 text-slate-200 rounded-tr-none" 
                  : "bg-slate-800/40 border border-glass text-slate-300 rounded-tl-none shadow-card"
              }`}>
                {msg.content}
              </div>
            </motion.div>
          ))}
          
          {/* Typing Indicator */}
          {isTyping && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
               <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 bg-neural-500/20 text-neural-400 border border-neural-500/30">
                  <Bot size={14} />
               </div>
               <div className="px-4 py-3 rounded-xl bg-slate-800/40 border border-glass flex items-center gap-2 rounded-tl-none shadow-card">
                  <Loader2 size={14} className="text-neural-400 animate-spin" />
                  <span className="font-mono text-[10px] text-slate-500 uppercase tracking-widest">Querying Vector Space...</span>
               </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="relative flex items-center mt-auto">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Ask a question about this document..."
          className="w-full bg-slate-950/60 border border-glass rounded-xl py-3.5 pl-4 pr-12 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-signal-500/50 transition-all shadow-inner"
        />
        <button
          type="submit"
          disabled={!inputValue.trim() || isTyping}
          className="absolute right-2 p-2 rounded-lg bg-signal-500/10 text-signal-400 hover:bg-signal-500/20 disabled:opacity-30 transition-colors"
        >
          <Send size={16} />
        </button>
      </form>
    </motion.div>
  );
}

// ── Main dashboard ─────────────────────────────────────────────
export default function ResultsDashboard({ data, fileName, onReset }) {
  return (
    <div className="min-h-screen px-4 py-8 md:px-6">
      {/* Header bar */}
      <motion.div
        className="max-w-6xl mx-auto flex items-center justify-between mb-8"
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-pulse-500 animate-pulse" />
            <span className="font-mono text-[10px] tracking-widest text-pulse-500 uppercase">
              Analysis Complete
            </span>
          </div>
          <h2 className="font-display text-2xl font-700 text-white">
            CADIS Results
          </h2>
        </div>

        <motion.button
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          onClick={onReset}
          className="
            flex items-center gap-2 px-4 py-2 rounded-xl glass-bright
            border border-glass-bright hover:border-signal-500/40
            font-body text-sm text-slate-400 hover:text-signal-300
            transition-colors duration-200
          "
        >
          <RotateCcw size={13} />
          New Document
        </motion.button>
      </motion.div>

      {/* Bento grid */}
      <motion.div
        className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 items-start"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Box 1 — Summary (tall, spans 2 rows on large screens) */}
        <div className="lg:col-span-1 lg:row-span-2">
          <SummaryCard data={data} />
        </div>

        {/* Box 2 — Entities */}
        <div className="lg:col-span-1">
          <EntitiesCard data={data} />
        </div>

        {/* Box 3 — Metadata */}
        <div className="lg:col-span-1">
          <MetadataCard data={data} fileName={fileName} />
        </div>

        {/* Box 4 — Raw JSON */}
        <div className="md:col-span-2 lg:col-span-2">
          <JsonViewer data={data} />
        </div>

        {/* Box 5 — RAG Chat (NEW) */}
        <div className="md:col-span-2 lg:col-span-3 mt-2">
          <ChatCard fileName={fileName} />
        </div>
      </motion.div>

      {/* Footer */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="text-center font-mono text-[10px] text-slate-700 tracking-widest uppercase mt-10"
      >
        CADIS v2.0 · Neural Analysis Platform · Results generated at {new Date().toLocaleTimeString()}
      </motion.p>
    </div>
  );
}
