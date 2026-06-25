import { useMemo } from "react";
import ModuleHeader from "@/components/ModuleHeader";
import ModuleNav from "@/components/ModuleNav";
import CompletionStrip from "@/components/CompletionStrip";
import PageFooter from "@/components/PageFooter";
import BorderGlow from "@/components/BorderGlow";
import NoDocument from "@/components/NoDocument";
import CountUp from "@/components/CountUp";
import { useDocument } from "@/context/DocumentContext";
import { Copy, Check } from "lucide-react";
import { useState } from "react";

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text).catch(() => {});
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="cursor-target p-2 rounded-md hover:bg-secondary transition"
      aria-label="Copy summary"
    >
      {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
    </button>
  );
}

export default function Module6() {
  const { doc } = useDocument();

  const analysis = useMemo(() => {
    if (!doc) return null;

    const text = doc.enriched_text || doc.extracted_text || "";
    const summary = doc.executive_summary || "";
    const origWords = text.split(/\s+/).filter(Boolean).length;
    const summaryWords = summary.split(/\s+/).filter(Boolean).length;
    const compression = origWords > 0 ? Math.round(((origWords - summaryWords) / origWords) * 100) : 0;

    const sentences = summary.split(/[.!?]+/).filter((s) => s.trim().length > 10);

    const entityCount = Object.values(doc.document_entities || {}).reduce(
      (a, arr) => a + (Array.isArray(arr) ? arr.length : 0), 0
    );

    return { text, summary, origWords, summaryWords, compression, sentences, entityCount };
  }, [doc]);

  if (!doc) return <NoDocument />;

  const stats = [
    { n: analysis.origWords, suffix: "", l: "ORIGINAL WORDS" },
    { n: analysis.summaryWords, suffix: "", l: "SUMMARY WORDS" },
    { n: analysis.compression, suffix: "%", l: "COMPRESSION RATIO" },
    { n: analysis.sentences.length, suffix: "", l: "KEY SENTENCES" },
    { n: analysis.entityCount, suffix: "", l: "ENTITIES FOUND" },
  ];

  return (
    <div className="px-8 py-8">
      <ModuleHeader
        code="MOD-06"
        title="Intelligent Summary Generator"
        subtitle={`DistilBART abstractive summary of "${doc.filename}". Latency: ${Math.round(doc.latency_ms?.distilbart || 0)}ms.`}
        current={6}
      />

      <section className="mt-10 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BorderGlow>
          <div className="p-6 relative">
            <div className="absolute top-4 right-4">
              <CopyBtn text={analysis.summary} />
            </div>
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-primary mb-3">
              EXECUTIVE SUMMARY · DISTILBART ABSTRACTIVE
            </div>
            <h2 className="font-display text-xl font-semibold mb-3">Executive Summary</h2>
            <p className="text-[15px] leading-7 text-foreground/90">
              {analysis.summary || "No summary was generated for this document."}
            </p>
          </div>
        </BorderGlow>

        <BorderGlow>
          <div className="p-6">
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent-foreground mb-3">
              KEY SENTENCES · EXTRACTED FROM SUMMARY
            </div>
            <h2 className="font-display text-xl font-semibold mb-3">Key Sentences</h2>
            <ul className="space-y-3">
              {analysis.sentences.map((s, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-2 h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                  <span className="text-sm text-foreground/90 leading-6">{s.trim()}.</span>
                </li>
              ))}
              {analysis.sentences.length === 0 && (
                <li className="text-sm text-muted-foreground">No key sentences extracted.</li>
              )}
            </ul>
          </div>
        </BorderGlow>
      </section>

      <section className="mt-8 grid grid-cols-2 md:grid-cols-5 gap-3">
        {stats.map((s) => (
          <BorderGlow key={s.l}>
            <div className="p-5">
              <div className="font-display text-3xl font-bold text-primary">
                <CountUp from={0} to={s.n} duration={1.5} separator="," className="font-display text-3xl font-bold text-primary" />{s.suffix}
              </div>
              <div className="mt-1 font-mono text-[10px] tracking-widest text-muted-foreground">{s.l}</div>
            </div>
          </BorderGlow>
        ))}
      </section>

      <BorderGlow className="mt-8">
        <section className="p-6">
          <h2 className="font-display text-xl font-semibold mb-4">Original vs Summary Comparison</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="font-mono text-[10px] text-muted-foreground mb-2 uppercase tracking-widest">Original ({analysis.origWords} words)</div>
              <div className="rounded-lg bg-muted/40 border border-border p-4 text-[13px] leading-relaxed text-foreground/70 max-h-60 overflow-y-auto no-scrollbar">
                {analysis.text.slice(0, 1500)}
                {analysis.text.length > 1500 && "…"}
              </div>
            </div>
            <div>
              <div className="font-mono text-[10px] text-primary mb-2 uppercase tracking-widest">Summary ({analysis.summaryWords} words · {analysis.compression}% compressed)</div>
              <div className="rounded-lg bg-primary/5 border border-primary/20 p-4 text-[13px] leading-relaxed text-foreground/90 max-h-60 overflow-y-auto no-scrollbar">
                {analysis.summary || "No summary generated."}
              </div>
            </div>
          </div>
        </section>
      </BorderGlow>

      <CompletionStrip
        text={`Module 6 Complete — Summary generated with ${analysis.compression}% compression. Full CADIS Pipeline Finished!`}
        celebrate
      />
      <ModuleNav prev={{ to: "/module-5", label: "MOD-05 · QA Engine" }} next={{ to: "/", label: "Back to Home" }} />
      <PageFooter />
    </div>
  );
}
