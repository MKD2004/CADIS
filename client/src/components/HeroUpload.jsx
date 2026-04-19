import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence, useMotionValue, useTransform } from "framer-motion";
import { Upload, FileText, Zap, AlertCircle, ChevronRight } from "lucide-react";

// ── Floating orb ───────────────────────────────────────────────
function Orb({ x, y, size, color, delay }) {
  return (
    <motion.div
      className="absolute rounded-full pointer-events-none"
      style={{
        left: `${x}%`,
        top: `${y}%`,
        width: size,
        height: size,
        background: color,
        filter: "blur(80px)",
      }}
      animate={{
        scale:   [1, 1.3, 1],
        opacity: [0.3, 0.6, 0.3],
        x:       [0, 20, 0],
        y:       [0, -15, 0],
      }}
      transition={{
        duration: 8,
        delay,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    />
  );
}

// ── Grid corner decoration ─────────────────────────────────────
function CornerDecor({ position }) {
  const classes = {
    "tl": "top-6 left-6 border-t border-l",
    "tr": "top-6 right-6 border-t border-r",
    "bl": "bottom-6 left-6 border-b border-l",
    "br": "bottom-6 right-6 border-b border-r",
  }[position];

  return (
    <motion.div
      className={`absolute w-8 h-8 border-signal-500/40 ${classes}`}
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6, delay: 0.8 }}
    />
  );
}

// ── Feature chip ───────────────────────────────────────────────
function FeatureChip({ icon: Icon, label, delay }) {
  return (
    <motion.div
      className="flex items-center gap-2 glass px-3 py-1.5 rounded-full"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      <Icon size={12} className="text-signal-400" />
      <span className="font-mono text-[10px] tracking-widest text-slate-400 uppercase">
        {label}
      </span>
    </motion.div>
  );
}

// ── Dropzone glow ring ─────────────────────────────────────────
const RING_VARIANTS = {
  idle: {
    scale: 1,
    opacity: 0,
    borderColor: "rgba(6,182,212,0)",
  },
  hover: {
    scale: [1, 1.02, 1],
    opacity: [0, 0.6, 0],
    borderColor: "rgba(6,182,212,0.8)",
    transition: { duration: 1.5, repeat: Infinity },
  },
  drag: {
    scale: [1, 1.04, 1.01],
    opacity: [0.4, 0.9, 0.5],
    borderColor: "rgba(6,182,212,1)",
    transition: { duration: 0.8, repeat: Infinity },
  },
};

export default function HeroUpload({ onFileAccepted, error }) {
  const [dragState, setDragState] = useState("idle"); // idle | hover | drag
  const [selectedFile, setSelectedFile] = useState(null);

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      setSelectedFile(accepted[0]);
      setDragState("idle");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
    onDragEnter: () => setDragState("drag"),
    onDragLeave: () => setDragState("idle"),
  });

  // Sync drag state
  useEffect(() => {
    if (!isDragActive && dragState === "drag") setDragState("idle");
  }, [isDragActive]);

  const handleSubmit = () => {
    if (selectedFile) onFileAccepted(selectedFile);
  };

  const isDragging = isDragActive || dragState === "drag";

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-4">
      {/* Ambient orbs */}
      <Orb x={15}  y={20}  size={400} color="rgba(6,182,212,0.12)"  delay={0}   />
      <Orb x={75}  y={65}  size={350} color="rgba(139,92,246,0.10)" delay={2}   />
      <Orb x={50}  y={90}  size={300} color="rgba(6,182,212,0.06)"  delay={4}   />

      {/* Corner decorations */}
      <CornerDecor position="tl" />
      <CornerDecor position="tr" />
      <CornerDecor position="bl" />
      <CornerDecor position="br" />

      {/* Header */}
      <motion.div
        className="text-center mb-14 z-10"
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* Eyebrow */}
        <motion.div
          className="flex items-center justify-center gap-2 mb-5"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <div className="h-px w-12 bg-gradient-to-r from-transparent to-signal-500/60" />
          <span className="font-mono text-[10px] tracking-[4px] text-signal-500 uppercase">
            Context-Aware Document Intelligence
          </span>
          <div className="h-px w-12 bg-gradient-to-l from-transparent to-signal-500/60" />
        </motion.div>

        {/* Title */}
        <h1 className="font-display text-7xl font-800 tracking-tight leading-none mb-4">
          <motion.span
            className="block text-white"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6 }}
          >
            CADIS
          </motion.span>
          <motion.span
            className="block text-gradient-signal text-5xl font-300 tracking-wider mt-1"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45, duration: 0.6 }}
          >
            Neural Analysis Platform
          </motion.span>
        </h1>

        {/* Subtitle */}
        <motion.p
          className="text-slate-500 font-body text-base max-w-sm mx-auto mt-4 leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          Upload a PDF. Watch six ML modules extract every signal from your document in real-time.
        </motion.p>

        {/* Feature chips */}
        <motion.div
          className="flex flex-wrap items-center justify-center gap-2 mt-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
        >
          <FeatureChip icon={Zap}      label="GliNER NER"         delay={0.75} />
          <FeatureChip icon={FileText} label="ChromaDB RAG"       delay={0.82} />
          <FeatureChip icon={Zap}      label="DistilBART Summary"  delay={0.89} />
          <FeatureChip icon={FileText} label="Zero-Shot QA"        delay={0.96} />
        </motion.div>
      </motion.div>

      {/* Drop zone */}
      <motion.div
        className="relative z-10 w-full max-w-xl"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.5, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* Pulsing glow ring (behind the card) */}
        <motion.div
          className="absolute inset-0 rounded-2xl border-2"
          variants={RING_VARIANTS}
          animate={isDragging ? "drag" : dragState === "hover" ? "hover" : "idle"}
          style={{ boxShadow: isDragging ? "0 0 60px rgba(6,182,212,0.25)" : "none" }}
        />

        {/* Drop zone card */}
        <div
          {...getRootProps()}
          onMouseEnter={() => !isDragging && setDragState("hover")}
          onMouseLeave={() => !isDragging && setDragState("idle")}
          className={`
            relative rounded-2xl border-2 cursor-pointer overflow-hidden
            transition-all duration-300 select-none
            ${isDragging
              ? "border-signal-400/70 bg-signal-900/10 shadow-signal"
              : "border-glass-bright hover:border-signal-500/30"
            }
          `}
        >
          <input {...getInputProps()} />

          {/* Scanline overlay when dragging */}
          <AnimatePresence>
            {isDragging && (
              <motion.div
                className="absolute inset-0 pointer-events-none z-0"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                style={{
                  background:
                    "repeating-linear-gradient(0deg, transparent, transparent 4px, rgba(6,182,212,0.03) 4px, rgba(6,182,212,0.03) 8px)",
                }}
              />
            )}
          </AnimatePresence>

          {/* Card content */}
          <div className="relative z-10 glass-bright rounded-2xl p-10 text-center">
            {/* Icon */}
            <motion.div
              className="flex items-center justify-center mx-auto mb-6"
              animate={isDragging ? { scale: 1.1, rotate: [0, -5, 5, 0] } : { scale: 1, rotate: 0 }}
              transition={{ duration: 0.4 }}
            >
              <div
                className={`
                  relative w-16 h-16 rounded-2xl flex items-center justify-center
                  ${isDragging ? "bg-signal-500/20" : "bg-slate-800/60"}
                  border transition-colors duration-300
                  ${isDragging ? "border-signal-400/60" : "border-glass-bright"}
                `}
              >
                {/* Glow behind icon */}
                {isDragging && (
                  <motion.div
                    className="absolute inset-0 rounded-2xl bg-signal-500/10"
                    animate={{ opacity: [0.3, 0.8, 0.3] }}
                    transition={{ duration: 1, repeat: Infinity }}
                  />
                )}
                <Upload
                  size={24}
                  className={`transition-colors duration-300 ${isDragging ? "text-signal-300" : "text-slate-400"}`}
                />
              </div>
            </motion.div>

            {/* Text */}
            <AnimatePresence mode="wait">
              {isDragging ? (
                <motion.div
                  key="drag-active"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2 }}
                >
                  <p className="font-display text-xl font-600 text-signal-300 mb-1">
                    Drop to begin analysis
                  </p>
                  <p className="font-mono text-xs text-signal-500/70 tracking-wider">
                    RELEASE FILE TO UPLOAD
                  </p>
                </motion.div>
              ) : selectedFile ? (
                <motion.div
                  key="file-selected"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <FileText size={14} className="text-signal-400" />
                    <p className="font-mono text-sm text-signal-300 truncate max-w-[220px]">
                      {selectedFile.name}
                    </p>
                  </div>
                  <p className="font-mono text-xs text-slate-500 tracking-wider">
                    {(selectedFile.size / 1024).toFixed(1)} KB · PDF
                  </p>
                </motion.div>
              ) : (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2 }}
                >
                  <p className="font-display text-xl font-600 text-slate-200 mb-1">
                    Drop your PDF here
                  </p>
                  <p className="font-body text-sm text-slate-500">
                    or{" "}
                    <span className="text-signal-400 hover:text-signal-300 transition-colors underline underline-offset-2">
                      browse files
                    </span>
                  </p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Specs */}
            {!isDragging && (
              <p className="font-mono text-[10px] text-slate-600 tracking-widest mt-4 uppercase">
                PDF · Max 50MB
              </p>
            )}
          </div>
        </div>

        {/* Submit button */}
        <AnimatePresence>
          {selectedFile && (
            <motion.button
              initial={{ opacity: 0, y: 12, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleSubmit}
              className="
                relative z-50 cursor-pointer pointer-events-auto  {/* <-- ADD THIS LINE */}
                w-full mt-3 py-3.5 px-6 rounded-xl
                bg-gradient-data
                font-display font-600 text-sm tracking-wide text-void
                flex items-center justify-center gap-2
                shadow-signal hover:shadow-signal-lg
                transition-shadow duration-300
              "
            >
              Begin Neural Analysis
              <ChevronRight size={16} />
            </motion.button>
          )}
        </AnimatePresence>

        {/* Error display */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="mt-3 overflow-hidden"
            >
              <div className="flex items-start gap-3 glass border-red-500/30 rounded-xl px-4 py-3">
                <AlertCircle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
                <p className="font-mono text-xs text-red-400 leading-relaxed">{error}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Bottom attribution */}
      <motion.p
        className="absolute bottom-6 font-mono text-[10px] tracking-widest text-slate-700 uppercase"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
      >
        CADIS v2.0 · Research Platform
      </motion.p>
    </div>
  );
}
