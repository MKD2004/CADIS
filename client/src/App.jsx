import { useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import axios from "axios";
import HeroUpload from "./components/HeroUpload";
import ProcessingTerminal from "./components/ProcessingTerminal";
import ResultsDashboard from "./components/ResultsDashboard";

// ── API endpoint ───────────────────────────────────────────────
const API_URL = "http://localhost:5000/api/process-pdf";

// ── Page transition variants ───────────────────────────────────
const pageVariants = {
  initial: { opacity: 0, y: 24, filter: "blur(8px)" },
  animate: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
  },
  exit: {
    opacity: 0,
    y: -16,
    filter: "blur(4px)",
    transition: { duration: 0.3, ease: [0.55, 0, 1, 0.45] },
  },
};

// ── View states ────────────────────────────────────────────────
const VIEWS = { IDLE: "idle", PROCESSING: "processing", RESULTS: "results" };

export default function App() {
  const [view,    setView]    = useState(VIEWS.IDLE);
  const [results, setResults] = useState(null);
  const [error,   setError]   = useState(null);
  const [file,    setFile]    = useState(null);

  // ── Submit handler ───────────────────────────────────────────
  const handleFileSubmit = useCallback(async (acceptedFile) => {
    setFile(acceptedFile);
    setError(null);
    setView(VIEWS.PROCESSING);

    const formData = new FormData();
    formData.append("file", acceptedFile);

    try {
      const { data } = await axios.post(API_URL, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        // Allow the terminal animation to play for at least 3s
        // even if the server responds faster
        timeout: 120_000,
      });

      // Minimum display time for the terminal (UX)
      await new Promise((r) => setTimeout(r, 3200));

      setResults(data);
      setView(VIEWS.RESULTS);
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        err.message ||
        "Connection refused. Is the CADIS backend running?";
      setError(message);
      setView(VIEWS.IDLE);
    }
  }, []);

  // ── Reset handler ────────────────────────────────────────────
  const handleReset = useCallback(() => {
    setView(VIEWS.IDLE);
    setResults(null);
    setFile(null);
    setError(null);
  }, []);

  return (
    // Ambient background layer
    <div className="relative min-h-screen bg-void overflow-hidden">
      {/* Static grid texture */}
      <div className="fixed inset-0 bg-grid opacity-100 pointer-events-none z-0" />

      {/* Main content */}
      <div className="relative z-10">
        <AnimatePresence mode="wait">
          {view === VIEWS.IDLE && (
            <motion.div
              key="hero"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <HeroUpload
                onFileAccepted={handleFileSubmit}
                error={error}
              />
            </motion.div>
          )}

          {view === VIEWS.PROCESSING && (
            <motion.div
              key="terminal"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <ProcessingTerminal fileName={file?.name} />
            </motion.div>
          )}

          {view === VIEWS.RESULTS && results && (
            <motion.div
              key="results"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <ResultsDashboard
                data={results}
                fileName={file?.name}
                onReset={handleReset}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
