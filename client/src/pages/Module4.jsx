import ModuleHeader from "@/components/ModuleHeader";
import ModuleNav from "@/components/ModuleNav";
import CompletionStrip from "@/components/CompletionStrip";
import PageFooter from "@/components/PageFooter";
import BorderGlow from "@/components/BorderGlow";
import NoDocument from "@/components/NoDocument";
import CountUp from "@/components/CountUp";
import { useDocument } from "@/context/DocumentContext";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

const AMBIGUITY_KEYWORDS = ["unclear", "ambiguity", "unknown", "inconclusive", "cannot determine", "suspected"];

const typeReference = [
  { t: "PP Attachment", d: "A prepositional phrase can attach to multiple parents.", ex: "I saw the man with binoculars." },
  { t: "Anaphoric", d: "A pronoun or referring expression has multiple possible antecedents.", ex: "Anna told Mira she was late." },
  { t: "Lexical", d: "A word carries multiple senses (polysemy) in context.", ex: "The bank was closed." },
  { t: "Semantic", d: "The sentence yields more than one valid logical interpretation.", ex: "Visiting relatives can be boring." },
];

export default function Module4() {
  const { doc } = useDocument();

  if (!doc) return <NoDocument />;

  const text = doc.enriched_text || doc.extracted_text || "";
  const ambiguitiesCount = doc.pipeline_flags?.ambiguities_found ?? 0;

  const foundKeywords = [];
  AMBIGUITY_KEYWORDS.forEach((kw) => {
    const regex = new RegExp(`\\b${kw}\\b`, "gi");
    let match;
    while ((match = regex.exec(text)) !== null) {
      const start = Math.max(0, match.index - 80);
      const end = Math.min(text.length, match.index + kw.length + 80);
      foundKeywords.push({
        keyword: kw,
        context: text.slice(start, end),
        position: match.index,
      });
    }
  });

  return (
    <div className="px-8 py-8">
      <ModuleHeader
        code="MOD-04"
        title="Ambiguity Detection and Resolution"
        subtitle={`Scanned "${doc.filename}" for ambiguous language patterns.`}
        badge="Novel Research Contribution"
        current={4}
      />

      <section className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4">
        <BorderGlow>
          <div className="p-5">
            <div className="font-display text-4xl font-bold text-[#fbbf24]">
              <CountUp from={0} to={ambiguitiesCount} duration={1.5} className="font-display text-4xl font-bold" />
            </div>
            <div className="mt-2 font-mono text-[10px] tracking-widest text-muted-foreground">AMBIGUITIES FOUND</div>
          </div>
        </BorderGlow>
        <BorderGlow>
          <div className="p-5">
            <div className="font-display text-4xl font-bold text-foreground">
              <CountUp from={0} to={AMBIGUITY_KEYWORDS.length} duration={1} className="font-display text-4xl font-bold" />
            </div>
            <div className="mt-2 font-mono text-[10px] tracking-widest text-muted-foreground">KEYWORDS SCANNED</div>
          </div>
        </BorderGlow>
        <BorderGlow>
          <div className="p-5 flex items-center gap-3">
            {ambiguitiesCount === 0 ? (
              <>
                <CheckCircle2 className="h-8 w-8 text-success" />
                <div>
                  <div className="font-display text-lg font-semibold text-success">No Ambiguities</div>
                  <div className="font-mono text-[10px] text-muted-foreground">Document is clear</div>
                </div>
              </>
            ) : (
              <>
                <AlertTriangle className="h-8 w-8 text-[#fbbf24]" />
                <div>
                  <div className="font-display text-lg font-semibold text-[#fbbf24]">Review Needed</div>
                  <div className="font-mono text-[10px] text-muted-foreground">{ambiguitiesCount} flags raised</div>
                </div>
              </>
            )}
          </div>
        </BorderGlow>
      </section>

      {foundKeywords.length > 0 && (
        <section className="mt-8">
          <h2 className="font-display text-2xl font-semibold mb-4">Ambiguous Language Detected</h2>
          <div className="space-y-4">
            {foundKeywords.map((f, i) => (
              <BorderGlow key={i}>
                <div className="p-6">
                  <span className="px-2.5 py-1 rounded-full bg-[#fbbf24]/15 text-[#fbbf24] border border-[#fbbf24]/30 font-mono text-[10px] uppercase tracking-widest">
                    {f.keyword}
                  </span>
                  <p className="mt-3 text-sm text-foreground/80 leading-relaxed font-mono">
                    …{f.context}…
                  </p>
                  <p className="mt-2 font-mono text-[10px] text-muted-foreground">
                    Position: character {f.position}
                  </p>
                </div>
              </BorderGlow>
            ))}
          </div>
        </section>
      )}

      {foundKeywords.length === 0 && ambiguitiesCount === 0 && (
        <section className="mt-8">
          <BorderGlow>
            <div className="p-8 text-center">
              <CheckCircle2 className="h-12 w-12 text-success mx-auto mb-4" />
              <h3 className="font-display text-xl font-semibold text-foreground mb-2">Document is Clear</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                No ambiguous language patterns were detected. The document uses clear, unambiguous phrasing throughout.
              </p>
            </div>
          </BorderGlow>
        </section>
      )}

      <section className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {typeReference.map((t) => (
          <BorderGlow key={t.t}>
            <div className="p-5">
              <div className="font-display text-base font-semibold text-primary">{t.t}</div>
              <p className="mt-2 text-sm text-muted-foreground">{t.d}</p>
              <p className="mt-3 text-xs italic text-foreground/70 font-mono">&ldquo;{t.ex}&rdquo;</p>
            </div>
          </BorderGlow>
        ))}
      </section>

      <CompletionStrip text={`Module 4 Complete — ${ambiguitiesCount} ambiguities detected via keyword scanning of "${doc.filename}".`} />
      <ModuleNav prev={{ to: "/module-3", label: "MOD-03 · NER + IE" }} next={{ to: "/module-5", label: "MOD-05 · QA Engine" }} />
      <PageFooter />
    </div>
  );
}
