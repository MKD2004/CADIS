import { useMemo } from "react";
import ModuleHeader from "@/components/ModuleHeader";
import ModuleNav from "@/components/ModuleNav";
import CompletionStrip from "@/components/CompletionStrip";
import PageFooter from "@/components/PageFooter";
import CountUp from "@/components/CountUp";
import BorderGlow from "@/components/BorderGlow";
import NoDocument from "@/components/NoDocument";
import { useDocument } from "@/context/DocumentContext";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

function tokenize(text) {
  const words = text.split(/\s+/).filter(Boolean);
  const sentences = text.split(/[.!?]+/).filter((s) => s.trim().length > 0);
  const uniqueLemmas = new Set(words.map((w) => w.toLowerCase().replace(/[^a-z0-9]/g, "")).filter(Boolean));
  return { words, sentences, uniqueLemmas };
}

export default function Module1() {
  const { doc } = useDocument();

  const analysis = useMemo(() => {
    if (!doc) return null;
    const text = doc.enriched_text || doc.extracted_text || "";
    const { words, sentences, uniqueLemmas } = tokenize(text);
    return { text, words, sentences, uniqueLemmas };
  }, [doc]);

  if (!doc) return <NoDocument />;

  const metrics = [
    { n: analysis.words.length, l: "TOTAL TOKENS", d: "from uploaded doc", up: true },
    { n: analysis.sentences.length, l: "SENTENCES", d: "split on .!?", up: true },
    { n: analysis.uniqueLemmas.size, l: "UNIQUE LEMMAS", d: "lowercase normalized", up: false },
    { n: doc.metadata?.chunks_stored || 0, l: "CHUNKS STORED", d: "in ChromaDB", up: true },
  ];

  const preview = analysis.words.slice(0, 60);

  const stopWords = new Set(["the","a","an","is","are","was","were","in","on","at","to","for","of","and","or","but","with","by","from","as","it","its","this","that","not","be","has","have","had","do","does","did","will","would","shall","should","can","could","may","might","no","so","if","then","than","very","just","also","about","up","out","into","over","after","before","between","under","through"]);

  return (
    <div className="px-8 py-8">
      <ModuleHeader
        code="MOD-01"
        title="NLP Preprocessing Engine"
        subtitle={`Tokenization and linguistic structure analysis of "${doc.filename || "uploaded document"}".`}
        current={1}
      />

      <section className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
        {metrics.map((m) => (
          <BorderGlow key={m.l}>
            <div className="p-5">
              <div className="font-mono text-[10px] tracking-widest text-muted-foreground">{m.l}</div>
              <div className="mt-2 font-display text-[34px] leading-none font-extrabold text-foreground">
                <CountUp from={0} to={m.n} duration={1.5} separator="," className="font-display text-[34px] leading-none font-extrabold" />
              </div>
              <div className={`mt-3 inline-flex items-center gap-1 text-[11px] font-medium ${m.up ? "text-success" : "text-primary"}`}>
                {m.up ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
                {m.d}
              </div>
            </div>
          </BorderGlow>
        ))}
      </section>

      <section className="mt-8 grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-8">
          <BorderGlow>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-lg font-semibold text-foreground">Token Stream Preview</h2>
                <span className="font-mono text-[10px] text-muted-foreground">first 60 tokens</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {preview.map((w, i) => {
                  const clean = w.toLowerCase().replace(/[^a-z]/g, "");
                  const isStop = stopWords.has(clean);
                  return (
                    <span
                      key={i}
                      className={`px-2.5 py-1 rounded-md text-[13px] border cursor-default transition hover:-translate-y-px ${
                        isStop
                          ? "bg-muted text-muted-foreground/60 border-border"
                          : "bg-primary/15 text-primary border-primary/30"
                      }`}
                    >
                      {w}
                    </span>
                  );
                })}
              </div>
              <div className="mt-4 flex gap-2 text-[10px] font-mono">
                <span className="px-2 py-0.5 rounded border bg-primary/15 text-primary border-primary/30">CONTENT</span>
                <span className="px-2 py-0.5 rounded border bg-muted text-muted-foreground/60 border-border">STOP</span>
              </div>
            </div>
          </BorderGlow>
        </div>

        <aside className="col-span-12 lg:col-span-4">
          <BorderGlow>
            <div className="p-6">
              <h3 className="font-display text-lg font-semibold text-foreground">Open vs Closed Class</h3>
              <div className="mt-4 space-y-3">
                {(() => {
                  const content = analysis.words.filter((w) => !stopWords.has(w.toLowerCase().replace(/[^a-z]/g, "")));
                  const stops = analysis.words.length - content.length;
                  const total = analysis.words.length || 1;
                  return [
                    { label: "Content Words", n: content.length, pct: ((content.length / total) * 100).toFixed(0), color: "var(--primary)" },
                    { label: "Stop Words", n: stops, pct: ((stops / total) * 100).toFixed(0), color: "var(--muted-foreground)" },
                  ].map((s) => (
                    <div key={s.label} className="flex items-center gap-3">
                      <span className="w-28 font-mono text-[11px] text-muted-foreground">{s.label}</span>
                      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${s.pct}%`, background: s.color }} />
                      </div>
                      <span className="w-12 text-right font-mono text-[11px] text-foreground/80">{s.n}</span>
                    </div>
                  ));
                })()}
              </div>
            </div>
          </BorderGlow>
        </aside>
      </section>

      <section className="mt-8">
        <BorderGlow>
          <div className="p-6">
            <h2 className="font-display text-lg font-semibold text-foreground mb-4">First 5 Sentences</h2>
            <div className="space-y-3">
              {analysis.sentences.slice(0, 5).map((s, i) => (
                <div key={i} className="flex gap-3">
                  <span className="font-mono text-[10px] text-primary mt-1 shrink-0">S{i + 1}</span>
                  <p className="text-sm text-foreground/80 leading-relaxed">{s.trim()}</p>
                </div>
              ))}
            </div>
          </div>
        </BorderGlow>
      </section>

      <CompletionStrip text={`Module 1 Complete — ${analysis.words.length} tokens extracted from "${doc.filename}".`} />
      <ModuleNav prev={{ to: "/", label: "Home" }} next={{ to: "/module-2", label: "MOD-02 · Semantic Embeddings" }} />
      <PageFooter />
    </div>
  );
}
