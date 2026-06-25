import { useMemo } from "react";
import ModuleHeader from "@/components/ModuleHeader";
import ModuleNav from "@/components/ModuleNav";
import PageFooter from "@/components/PageFooter";
import CompletionStrip from "@/components/CompletionStrip";
import CountUp from "@/components/CountUp";
import BorderGlow from "@/components/BorderGlow";
import NoDocument from "@/components/NoDocument";
import { useDocument } from "@/context/DocumentContext";

const ENTITY_COLORS = {
  PERSON: "#60a5fa",
  COMPANY: "#fbbf24",
  ORGANIZATION: "#fbbf24",
  LOCATION: "#34d399",
  DATE: "#a78bfa",
  MONEY: "#fbbf24",
  "THREAT ACTOR": "#f472b6",
  MALWARE: "#f87171",
  VULNERABILITY: "#fb923c",
  "IP ADDRESS": "#22d3ee",
};

function getColor(label) {
  return ENTITY_COLORS[label?.toUpperCase()] || "#a78bfa";
}

export default function Module3() {
  const { doc } = useDocument();

  const { entityCounts, allEntities } = useMemo(() => {
    if (!doc?.document_entities) return { entityCounts: [], allEntities: [] };

    const entities = doc.document_entities;
    const counts = Object.entries(entities).map(([label, arr]) => ({
      k: label.toUpperCase(),
      v: Array.isArray(arr) ? arr.length : 0,
      color: getColor(label),
    }));

    const flat = Object.entries(entities).flatMap(([label, arr]) =>
      (Array.isArray(arr) ? arr : []).map((e) => ({
        text: e.text,
        label: (e.label || label).toUpperCase(),
        score: e.score,
        start: e.start,
        end: e.end,
      }))
    );

    return { entityCounts: counts, allEntities: flat };
  }, [doc]);

  if (!doc) return <NoDocument />;

  const text = doc.enriched_text || doc.extracted_text || "";
  const totalEntities = allEntities.length;

  return (
    <div className="px-8 py-8">
      <ModuleHeader
        code="MOD-03"
        title="NER + Information Extraction"
        subtitle={`GliNER zero-shot NER extracted ${totalEntities} entities from "${doc.filename}".`}
        current={3}
      />

      <section className="mt-10 grid grid-cols-2 md:grid-cols-6 gap-3">
        {entityCounts.map((e) => (
          <BorderGlow key={e.k}>
            <div className="p-4">
              <div className="font-display text-3xl font-bold" style={{ color: e.color }}>
                <CountUp from={0} to={e.v} duration={1.5} className="font-display text-3xl font-bold" />
              </div>
              <div className="mt-1 font-mono text-[10px] tracking-widest text-muted-foreground">{e.k}</div>
            </div>
          </BorderGlow>
        ))}
      </section>

      <section className="mt-8">
        <BorderGlow>
          <div className="p-6">
            <h2 className="font-display text-xl font-semibold mb-4">All Extracted Entities</h2>
            <div className="flex flex-wrap gap-2">
              {allEntities.map((e, i) => {
                const color = getColor(e.label);
                return (
                  <span
                    key={`${e.text}-${i}`}
                    className="relative inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[12px] font-mono"
                    style={{
                      borderColor: `${color}66`,
                      background: `${color}1a`,
                      color: color,
                    }}
                  >
                    <span className="font-mono text-[8px] tracking-widest opacity-60">{e.label}</span>
                    <span className="mx-1 w-px h-3 opacity-30" style={{ background: color }} />
                    {e.text}
                    {e.score !== undefined && (
                      <span className="opacity-50 text-[9px] ml-1">{(e.score * 100).toFixed(0)}%</span>
                    )}
                  </span>
                );
              })}
              {allEntities.length === 0 && (
                <p className="font-mono text-xs text-muted-foreground py-4">No entities extracted.</p>
              )}
            </div>
          </div>
        </BorderGlow>
      </section>

      <section className="mt-8">
        <BorderGlow>
          <div className="p-6">
            <h2 className="font-display text-xl font-semibold mb-4">Annotated Text Preview</h2>
            <p className="text-[14px] leading-8 text-foreground/80">
              {(() => {
                const snippet = text.slice(0, 1500);
                const sorted = [...allEntities]
                  .filter((e) => e.start != null && e.end != null && e.end <= 1500)
                  .sort((a, b) => a.start - b.start);

                if (sorted.length === 0) return snippet;

                const parts = [];
                let cursor = 0;
                for (const ent of sorted) {
                  if (ent.start > cursor) {
                    parts.push(<span key={`t-${cursor}`}>{snippet.slice(cursor, ent.start)}</span>);
                  }
                  const color = getColor(ent.label);
                  parts.push(
                    <span
                      key={`e-${ent.start}`}
                      className="relative inline-block mx-0.5 px-1.5 py-0.5 rounded border"
                      style={{ borderColor: `${color}66`, background: `${color}1f`, color }}
                    >
                      <span className="absolute -top-3 left-1 font-mono text-[8px] tracking-widest" style={{ color }}>
                        {ent.label}
                      </span>
                      {snippet.slice(ent.start, ent.end)}
                    </span>
                  );
                  cursor = ent.end;
                }
                if (cursor < snippet.length) {
                  parts.push(<span key={`t-${cursor}`}>{snippet.slice(cursor)}</span>);
                }
                return parts.length > 0 ? parts : snippet;
              })()}
            </p>
          </div>
        </BorderGlow>
      </section>

      <section className="mt-8">
        <BorderGlow>
          <div className="overflow-hidden">
            <div className="px-6 py-3 border-b border-border flex items-center justify-between" style={{ background: "#0a0a12" }}>
              <h2 className="font-display text-base font-semibold text-white">Structured JSON Output</h2>
              <div className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-destructive/70" />
                <span className="h-2.5 w-2.5 rounded-full bg-accent/70" />
                <span className="h-2.5 w-2.5 rounded-full bg-success/70" />
              </div>
            </div>
            <pre className="p-6 font-mono text-[12px] leading-relaxed overflow-x-auto text-foreground/70 max-h-72 no-scrollbar" style={{ background: "#0a0a12" }}>
              {JSON.stringify(doc.document_entities, null, 2)}
            </pre>
          </div>
        </BorderGlow>
      </section>

      <CompletionStrip text={`Module 3 Complete — GliNER extracted ${totalEntities} entities across ${entityCounts.length} categories. Latency: ${Math.round(doc.latency_ms?.gliner || 0)}ms.`} />
      <ModuleNav prev={{ to: "/module-2", label: "MOD-02 · Embeddings" }} next={{ to: "/module-4", label: "MOD-04 · Ambiguity" }} />
      <PageFooter />
    </div>
  );
}
