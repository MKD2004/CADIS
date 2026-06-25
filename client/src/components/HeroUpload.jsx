import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { AnimatePresence } from "framer-motion";
import { motion } from "motion/react";
import { Upload, FileText, Zap, AlertCircle, ChevronRight, FlaskConical, Loader2 } from "lucide-react";
import { fetchSamples } from "@/lib/api";
import BorderGlow from "@/components/BorderGlow";

export default function HeroUpload({ onFileAccepted, onSampleSelect, error, isProcessing }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [samples, setSamples] = useState([]);
  const [loadingSample, setLoadingSample] = useState(null);

  useEffect(() => {
    fetchSamples().then(setSamples).catch(() => {});
  }, []);

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      setSelectedFile(accepted[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
    disabled: isProcessing,
  });

  const handleSubmit = () => {
    if (selectedFile && onFileAccepted) onFileAccepted(selectedFile);
  };

  return (
    <div className="flex flex-col items-center justify-center px-4 py-20">
      {/* Header */}
      <motion.div
        className="text-center mb-12"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="flex items-center justify-center gap-2 mb-4">
          <div className="h-px w-12 bg-gradient-to-r from-transparent to-primary/60" />
          <span className="font-mono text-[10px] tracking-[4px] text-primary uppercase">
            Neural Document Analysis
          </span>
          <div className="h-px w-12 bg-gradient-to-l from-transparent to-primary/60" />
        </div>

        <h2 className="font-display text-4xl md:text-5xl font-extrabold tracking-tight text-white mb-3">
          Upload & Analyze
        </h2>
        <p className="text-white/50 text-[15px] max-w-md mx-auto leading-relaxed">
          Drop a PDF and watch six ML modules extract every signal from your document.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-2 mt-5">
          {["GliNER NER", "ChromaDB RAG", "DistilBART", "RoBERTa QA"].map((s) => (
            <span
              key={s}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/[0.06] font-mono text-[10px] text-white/50"
            >
              <Zap className="h-2.5 w-2.5 text-primary" />
              {s}
            </span>
          ))}
        </div>
      </motion.div>

      {/* Drop zone */}
      <motion.div
        className="w-full max-w-xl"
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        <BorderGlow>
          <div
            {...getRootProps()}
            className={`
              relative rounded-xl p-10 text-center cursor-pointer transition-all duration-300
              ${isDragActive
                ? "bg-primary/5 border border-primary/30"
                : "hover:bg-white/[0.02]"
              }
              ${isProcessing ? "pointer-events-none opacity-60" : ""}
            `}
          >
            <input {...getInputProps()} />

            <div className="flex items-center justify-center mx-auto mb-5">
              <div
                className={`
                  w-14 h-14 rounded-xl flex items-center justify-center border transition-all duration-300
                  ${isDragActive
                    ? "bg-primary/15 border-primary/40"
                    : "bg-white/[0.03] border-white/[0.06]"
                  }
                `}
              >
                {isProcessing ? (
                  <Loader2 className="h-6 w-6 text-primary animate-spin" />
                ) : (
                  <Upload
                    className={`h-6 w-6 transition-colors ${isDragActive ? "text-primary" : "text-white/40"}`}
                  />
                )}
              </div>
            </div>

            <AnimatePresence mode="wait">
              {isProcessing ? (
                <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <p className="font-display text-lg font-semibold text-primary mb-1">
                    Processing document…
                  </p>
                  <p className="font-mono text-[11px] text-white/40 tracking-wider uppercase">
                    Running neural pipeline
                  </p>
                </motion.div>
              ) : isDragActive ? (
                <motion.div key="drag" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <p className="font-display text-lg font-semibold text-primary mb-1">
                    Drop to begin analysis
                  </p>
                  <p className="font-mono text-[11px] text-white/40 tracking-wider uppercase">
                    Release file to upload
                  </p>
                </motion.div>
              ) : selectedFile ? (
                <motion.div key="selected" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <div className="flex items-center justify-center gap-2 mb-1">
                    <FileText className="h-4 w-4 text-primary" />
                    <p className="font-mono text-sm text-white/80 truncate max-w-[220px]">
                      {selectedFile.name}
                    </p>
                  </div>
                  <p className="font-mono text-[11px] text-white/40 tracking-wider">
                    {(selectedFile.size / 1024).toFixed(1)} KB · PDF
                  </p>
                </motion.div>
              ) : (
                <motion.div key="idle" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <p className="font-display text-lg font-semibold text-white/90 mb-1">
                    Drop your PDF here
                  </p>
                  <p className="text-sm text-white/40">
                    or <span className="text-primary hover:text-primary/80 transition-colors underline underline-offset-2 cursor-pointer">browse files</span>
                  </p>
                </motion.div>
              )}
            </AnimatePresence>

            {!isDragActive && !isProcessing && (
              <p className="font-mono text-[10px] text-white/20 tracking-widest mt-4 uppercase">
                PDF · Max 50 MB
              </p>
            )}
          </div>
        </BorderGlow>

        {/* Submit button */}
        <AnimatePresence>
          {selectedFile && !isProcessing && (
            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              onClick={handleSubmit}
              className="
                cursor-target w-full mt-3 py-3.5 px-6 rounded-xl
                bg-primary text-white font-display font-semibold text-sm tracking-wide
                flex items-center justify-center gap-2
                shadow-lg shadow-primary/30 hover:shadow-primary/50
                hover:translate-y-[-1px] transition-all duration-200
              "
            >
              Begin Neural Analysis
              <ChevronRight className="h-4 w-4" />
            </motion.button>
          )}
        </AnimatePresence>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 overflow-hidden"
            >
              <div className="flex items-start gap-3 rounded-xl px-4 py-3 bg-red-500/10 border border-red-500/20">
                <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" />
                <p className="font-mono text-xs text-red-400 leading-relaxed">{error}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Sample documents */}
      {samples.length > 0 && !isProcessing && (
        <motion.div
          className="w-full max-w-xl mt-8"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.4 }}
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-white/[0.06]" />
            <span className="font-mono text-[10px] tracking-[3px] text-white/30 uppercase">
              or try a sample
            </span>
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-white/[0.06]" />
          </div>

          <div className="flex flex-col gap-2">
            {samples.map((sample) => (
              <button
                key={sample.document_id}
                disabled={loadingSample !== null}
                onClick={() => {
                  setLoadingSample(sample.document_id);
                  if (onSampleSelect) onSampleSelect(sample);
                }}
                className="
                  cursor-target group w-full flex items-center gap-3 px-4 py-3
                  rounded-xl border border-white/[0.06]
                  hover:border-primary/30 hover:bg-primary/[0.03]
                  transition-all duration-200 text-left
                  disabled:opacity-50 disabled:cursor-wait
                "
              >
                <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                  {loadingSample === sample.document_id ? (
                    <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
                  ) : (
                    <FlaskConical className="h-3.5 w-3.5 text-primary" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-white/80 truncate">
                      {sample.title}
                    </span>
                    <span className="font-mono text-[9px] tracking-wider text-primary bg-primary/10 px-1.5 py-0.5 rounded-full flex-shrink-0 uppercase">
                      Sample
                    </span>
                  </div>
                </div>
                <ChevronRight className="h-3.5 w-3.5 text-white/20 group-hover:text-primary transition-colors flex-shrink-0" />
              </button>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
