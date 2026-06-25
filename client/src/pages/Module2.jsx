import { useState } from "react";
import ModuleHeader from "@/components/ModuleHeader";
import ModuleNav from "@/components/ModuleNav";
import PageFooter from "@/components/PageFooter";
import CompletionStrip from "@/components/CompletionStrip";
import CountUp from "@/components/CountUp";
import BorderGlow from "@/components/BorderGlow";
import NoDocument from "@/components/NoDocument";
import { useDocument } from "@/context/DocumentContext";
import { Search, Loader2 } from "lucide-react";
import { chat } from "@/lib/api";

export default function Module2() {
  const { doc } = useDocument();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);

  if (!doc) return <NoDocument />;

  const chunks = doc.metadata?.chunks_stored || 0;
  const text = doc.enriched_text || doc.extracted_text || "";
  const sentences = text.split(/[.!?]+/).filter((s) => s.trim().length > 10);

  const metrics = [
    { n: chunks, l: "CHUNKS STORED" },
    { n: 384, l: "EMBEDDING DIMS", mono: true },
    { v: "all-MiniLM-L6-v2", l: "MODEL NAME", mono: true },
  ];

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await chat(query, doc.document_id);
      setResults(res);
    } catch {
      setResults({ answer: "Search failed — backend may be unavailable.", latency_ms: {} });
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="px-8 py-8">
      <ModuleHeader
        code="MOD-02"
        title="Semantic Embedding Module"
        subtitle={`Dense vector representations of "${doc.filename}" — ${chunks} chunks embedded with MiniLM.`}
        current={2}
      />

      <section className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4">
        {metrics.map((m) => (
          <BorderGlow key={m.l}>
            <div className="p-5">
              <div className={`font-bold text-foreground ${m.mono ? "font-mono text-xl break-all" : "font-display text-4xl"}`}>
                {m.n != null ? (
                  <CountUp from={0} to={m.n} duration={1.5} separator="," className={`font-bold text-foreground ${m.mono ? "font-mono text-xl break-all" : "font-display text-4xl"}`} />
                ) : m.v}
              </div>
              <div className="mt-2 font-mono text-[10px] tracking-widest text-muted-foreground">{m.l}</div>
            </div>
          </BorderGlow>
        ))}
      </section>

      <section className="mt-8">
        <BorderGlow>
          <div className="p-6">
            <h2 className="font-display text-xl font-semibold mb-4">Embedded Sentences Preview</h2>
            <div className="space-y-2 max-h-80 overflow-y-auto no-scrollbar">
              {sentences.slice(0, 15).map((s, i) => (
                <div key={i} className="flex items-start gap-3 py-2 border-b border-border/40 last:border-0">
                  <span className="font-mono text-[10px] text-primary mt-1 shrink-0 w-8">S{i + 1}</span>
                  <p className="text-[13px] text-foreground/80 leading-relaxed">{s.trim()}</p>
                </div>
              ))}
            </div>
            {sentences.length > 15 && (
              <p className="mt-3 font-mono text-[10px] text-muted-foreground">+ {sentences.length - 15} more sentences embedded</p>
            )}
          </div>
        </BorderGlow>
      </section>

      <section className="mt-8">
        <BorderGlow>
          <div className="p-6">
            <h2 className="font-display text-xl font-semibold">Semantic Search</h2>
            <p className="mt-1 text-sm text-muted-foreground">Query the embedded document using natural language.</p>
            <div className="mt-4 flex items-center gap-2 p-2 rounded-xl bg-background border border-border focus-within:border-primary transition">
              <Search className="h-4 w-4 text-muted-foreground ml-2" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Enter a question to search semantically..."
                className="flex-1 bg-transparent outline-none text-sm py-2 font-mono placeholder:text-muted-foreground"
              />
              <button
                onClick={handleSearch}
                disabled={searching || !query.trim()}
                className="cursor-target px-4 py-2 rounded-lg bg-primary text-primary-foreground font-mono text-xs inline-flex items-center gap-2 disabled:opacity-40 transition"
              >
                {searching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "SEARCH"}
              </button>
            </div>

            {results && (
              <div className="mt-6">
                <BorderGlow>
                  <div className="p-5 border-l-4 border-l-primary">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-[11px] text-primary">ANSWER</span>
                      {results.latency_ms && (
                        <span className="font-mono text-[10px] text-muted-foreground">
                          MiniLM: {Math.round(results.latency_ms.minilm || 0)}ms · RoBERTa: {Math.round(results.latency_ms.roberta || 0)}ms
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-foreground/90 leading-relaxed">{results.answer}</p>
                  </div>
                </BorderGlow>
              </div>
            )}
          </div>
        </BorderGlow>
      </section>

      <CompletionStrip text={`Module 2 Complete — ${chunks} chunks embedded with 384-dim MiniLM vectors. Semantic search operational.`} />
      <ModuleNav prev={{ to: "/module-1", label: "MOD-01 · Preprocessing" }} next={{ to: "/module-3", label: "MOD-03 · NER + IE" }} />
      <PageFooter />
    </div>
  );
}
