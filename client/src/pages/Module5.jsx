import { useState } from "react";
import ModuleHeader from "@/components/ModuleHeader";
import ModuleNav from "@/components/ModuleNav";
import CompletionStrip from "@/components/CompletionStrip";
import PageFooter from "@/components/PageFooter";
import BorderGlow from "@/components/BorderGlow";
import NoDocument from "@/components/NoDocument";
import { useDocument } from "@/context/DocumentContext";
import { chat } from "@/lib/api";
import { Sparkles, Loader2, HelpCircle, Zap, MessageSquare } from "lucide-react";

export default function Module5() {
  const { doc } = useDocument();
  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(false);

  if (!doc) return <NoDocument />;

  const handleAsk = async () => {
    if (!question.trim() || loading) return;
    const q = question;
    setQuestion("");
    setLoading(true);

    try {
      const res = await chat(q, doc.document_id);
      setAnswers((prev) => [
        {
          question: q,
          answer: res.answer || "No answer found.",
          latency: res.latency_ms || {},
        },
        ...prev,
      ]);
    } catch {
      setAnswers((prev) => [
        { question: q, answer: "Error: Could not reach the QA backend.", latency: {} },
        ...prev,
      ]);
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    "What is this document about?",
    "Who are the main people or organizations mentioned?",
    "What are the key findings?",
    "What dates or events are referenced?",
    "What is the conclusion?",
  ];

  return (
    <div className="px-8 py-8">
      <ModuleHeader
        code="MOD-05"
        title="Extractive Question Answering"
        subtitle={`Ask questions about "${doc.filename}" — powered by ChromaDB retrieval + RoBERTa extraction.`}
        current={5}
      />

      <div className="mt-8 grid grid-cols-12 gap-6">
        <div className="col-span-12 xl:col-span-8 space-y-6">
          <BorderGlow>
            <section className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-lg font-semibold flex items-center gap-2">
                  <HelpCircle className="h-5 w-5 text-primary" /> Ask Your Document
                </h2>
                <div className="flex gap-2">
                  <span className="px-2.5 py-1 rounded-md bg-accent text-accent-foreground font-mono text-[10px]">RoBERTa QA</span>
                  <span className="px-2.5 py-1 rounded-md bg-muted text-foreground/80 font-mono text-[10px]">MiniLM Retrieval</span>
                </div>
              </div>
              <div className="rounded-xl border border-border bg-muted/40 p-4">
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                  className="w-full bg-transparent outline-none text-[14px] placeholder:text-muted-foreground"
                  placeholder="Type your question about the document..."
                />
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex flex-wrap gap-1.5">
                    {suggestedQuestions.slice(0, 3).map((sq) => (
                      <button
                        key={sq}
                        onClick={() => setQuestion(sq)}
                        className="font-mono text-[9px] text-primary/60 hover:text-primary bg-primary/5 hover:bg-primary/10 px-2 py-1 rounded-md transition"
                      >
                        {sq}
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={handleAsk}
                    disabled={!question.trim() || loading}
                    className="cursor-target px-4 h-10 rounded-lg bg-foreground text-background font-medium text-[13px] inline-flex items-center gap-2 hover:opacity-90 disabled:opacity-40 transition"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    {loading ? "Extracting…" : "Extract Answer"}
                  </button>
                </div>
              </div>
            </section>
          </BorderGlow>

          {answers.length > 0 && (
            <BorderGlow>
              <section className="overflow-hidden">
                <div className="px-6 pt-5 pb-3 flex items-center justify-between">
                  <h2 className="font-mono text-[11px] tracking-widest text-muted-foreground">
                    <MessageSquare className="h-3.5 w-3.5 inline mr-1" />
                    EXTRACTED ANSWERS ({answers.length})
                  </h2>
                </div>
                <div className="divide-y divide-border">
                  {answers.map((qa, i) => (
                    <div key={i} className="px-6 py-4 hover:bg-muted/40 transition">
                      <div className="text-[13px] text-muted-foreground mb-2">Q: {qa.question}</div>
                      <div className="flex items-start gap-3">
                        <span className="px-3 py-1.5 rounded-md bg-primary/10 text-primary border border-primary/20 font-mono text-[13px] leading-relaxed flex-1">
                          {qa.answer}
                        </span>
                      </div>
                      {(qa.latency.minilm || qa.latency.roberta) && (
                        <div className="mt-2 flex gap-3">
                          {qa.latency.minilm > 0 && (
                            <span className="inline-flex items-center gap-1 font-mono text-[10px] text-primary/60">
                              <Zap className="h-2.5 w-2.5" /> MiniLM: {Math.round(qa.latency.minilm)}ms
                            </span>
                          )}
                          {qa.latency.roberta > 0 && (
                            <span className="inline-flex items-center gap-1 font-mono text-[10px] text-primary/60">
                              <Zap className="h-2.5 w-2.5" /> RoBERTa: {Math.round(qa.latency.roberta)}ms
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            </BorderGlow>
          )}

          <BorderGlow>
            <section className="p-6">
              <h2 className="font-display text-lg font-semibold flex items-center gap-2 mb-3">
                Source Context
              </h2>
              <span className="font-mono text-[11px] text-muted-foreground">{doc.filename}</span>
              <div className="mt-3 rounded-lg bg-muted/40 border border-border p-4 text-[13px] leading-relaxed text-foreground/80 max-h-60 overflow-y-auto no-scrollbar">
                {(doc.enriched_text || doc.extracted_text || "").slice(0, 2000)}
                {(doc.enriched_text || "").length > 2000 && "…"}
              </div>
            </section>
          </BorderGlow>
        </div>

        <aside className="col-span-12 xl:col-span-4 space-y-4">
          <BorderGlow>
            <div className="p-5">
              <div className="font-mono text-[11px] tracking-widest text-muted-foreground mb-3">SUGGESTED QUESTIONS</div>
              <div className="space-y-2">
                {suggestedQuestions.map((sq) => (
                  <button
                    key={sq}
                    onClick={() => { setQuestion(sq); }}
                    className="w-full text-left px-3 py-2.5 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/[0.03] text-sm text-foreground/70 hover:text-foreground transition"
                  >
                    {sq}
                  </button>
                ))}
              </div>
            </div>
          </BorderGlow>

          <BorderGlow backgroundColor="#0a0a12">
            <div className="p-5 text-white">
              <div className="font-mono text-[11px] tracking-widest text-white/60 mb-3">HOW IT WORKS</div>
              <div className="space-y-3 text-[13px] text-white/70">
                <div className="flex gap-2">
                  <span className="text-primary font-mono text-[11px] shrink-0">1.</span>
                  <span>Your question is embedded with MiniLM-L6-v2</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-primary font-mono text-[11px] shrink-0">2.</span>
                  <span>Top-3 relevant chunks retrieved from ChromaDB</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-primary font-mono text-[11px] shrink-0">3.</span>
                  <span>RoBERTa extracts the exact answer span</span>
                </div>
              </div>
            </div>
          </BorderGlow>
        </aside>
      </div>

      <CompletionStrip text={`Module 5 Complete — ${answers.length} questions answered from "${doc.filename}". Every answer grounded in the document.`} />
      <ModuleNav prev={{ to: "/module-4", label: "MOD-04 · Ambiguity" }} next={{ to: "/module-6", label: "MOD-06 · Summary" }} />
      <PageFooter />
    </div>
  );
}
