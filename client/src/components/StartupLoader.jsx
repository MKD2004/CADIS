import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";

const STEPS = [
  "Initializing GLiNER...",
  "Loading RoBERTa...",
  "Loading DistilBART...",
  "Connecting to ChromaDB...",
];

const HEALTH_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/health`
  : "/health";

export default function StartupLoader({ children }) {
  const [ready, setReady] = useState(false);
  const [hiding, setHiding] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [slow, setSlow] = useState(false);
  const mountTime = useRef(Date.now());

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const { data } = await axios.get(HEALTH_URL, { timeout: 3000 });
        if (!cancelled && data.ml_backend && data.ml_backend.status === "ok") {
          setHiding(true);
          setTimeout(() => setReady(true), 600);
          return;
        }
      } catch (_) {}

      if (!cancelled) {
        if (Date.now() - mountTime.current > 120_000) setSlow(true);
        setTimeout(poll, 3000);
      }
    };

    poll();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (ready) return;
    const id = setInterval(() => {
      setStepIndex((i) => (i < STEPS.length - 1 ? i + 1 : i));
    }, 8000);
    return () => clearInterval(id);
  }, [ready]);

  if (ready) return children;

  return (
    <>
      <AnimatePresence>
        {!hiding && (
          <motion.div
            key="loader"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6, ease: "easeInOut" }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-void"
          >
            {/* Background grid */}
            <div className="absolute inset-0 bg-grid-pattern bg-grid-40 opacity-30 animate-grid-drift" />

            {/* Glow orb */}
            <div
              className="absolute w-[400px] h-[400px] rounded-full opacity-20 animate-pulse-slow"
              style={{
                background:
                  "radial-gradient(circle, rgba(6,182,212,0.4) 0%, transparent 70%)",
              }}
            />

            <div className="relative flex flex-col items-center gap-8">
              {/* Spinner ring */}
              <div className="relative w-20 h-20">
                <div
                  className="absolute inset-0 rounded-full border-2 border-signal-800/40"
                />
                <div
                  className="absolute inset-0 rounded-full border-2 border-transparent border-t-signal-400 animate-spin"
                  style={{ animationDuration: "1.2s" }}
                />
                <div className="absolute inset-3 rounded-full bg-signal-500/10 animate-pulse-slow" />
              </div>

              {/* Status text */}
              <div className="flex flex-col items-center gap-3">
                <h2 className="font-display text-xl text-white/90 tracking-wide">
                  Waking up the AI models
                </h2>
                <p className="font-mono text-sm text-white/40 max-w-xs text-center">
                  This takes about 30 seconds on first load
                </p>
              </div>

              {/* Step indicator */}
              <div className="flex flex-col items-center gap-3 min-h-[72px]">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={stepIndex}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.3 }}
                    className="flex items-center gap-2"
                  >
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-signal-400 animate-pulse" />
                    <span className="font-mono text-sm text-signal-300">
                      {STEPS[stepIndex]}
                    </span>
                  </motion.div>
                </AnimatePresence>

                {/* Step dots */}
                <div className="flex gap-2">
                  {STEPS.map((_, i) => (
                    <div
                      key={i}
                      className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${
                        i <= stepIndex ? "bg-signal-400" : "bg-white/10"
                      }`}
                    />
                  ))}
                </div>
              </div>

              {/* Slow warning */}
              {slow && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="font-mono text-xs text-data-400/80 max-w-sm text-center mt-2"
                >
                  Taking longer than usual — the models are still loading.
                  Please wait.
                </motion.p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      {hiding && children}
    </>
  );
}
