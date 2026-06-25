import { Link } from "react-router-dom";
import { ArrowRight, Play, Shield, Lock, Cpu, CheckCircle2 } from "lucide-react";
import PageFooter from "@/components/PageFooter";
import CountUp from "@/components/CountUp";
import DecryptedText from "@/components/DecryptedText";
import TextType from "@/components/TextType";

export default function Home() {
  return (
    <div className="animate-float-up">
      {/* HERO — full viewport */}
      <section className="relative min-h-[calc(100vh-3.5rem)] flex flex-col items-center justify-center text-center px-10">
        <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 backdrop-blur border border-white/10 font-mono text-[10px] uppercase tracking-[0.2em] text-white/70">
          Introducing CADIS
        </span>
        <h1 className="mt-6 text-[12rem] md:text-[16rem] lg:text-[20rem] leading-[0.85] font-normal tracking-tighter text-white" style={{ fontFamily: "'Play', sans-serif" }}>
          CADIS
        </h1>
        <p className="mt-4 max-w-2xl font-display text-2xl font-semibold tracking-tight text-white/80">
          Context-Aware Document Intelligence System
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/analyze"
            className="cursor-target inline-flex items-center gap-2 h-11 px-5 rounded-lg bg-primary text-primary-foreground text-[14px] font-medium hover:translate-y-[-1px] transition shadow-lg shadow-primary/30"
          >
            Upload Document <ArrowRight className="h-4 w-4" />
          </Link>
          <button className="cursor-target inline-flex items-center gap-2 h-11 px-5 rounded-lg bg-white/5 backdrop-blur text-white text-[14px] font-medium border border-white/10 hover:bg-white/10 transition">
            <Play className="h-4 w-4" /> View Demo
          </button>
        </div>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-2 font-mono text-[11px] text-white/50">
          {["100% LOCAL", "ZERO CLOUD APIS", "6 NEURAL MODULES"].map((s) => (
            <span
              key={s}
              className="px-2.5 py-1 rounded-full bg-white/5 border border-white/[0.06]"
            >
              {s}
            </span>
          ))}
        </div>
      </section>

      {/* DOCS IN INTELLIGENCE OUT */}
      <section className="pt-24 grid grid-cols-12 gap-6 px-10">
        <div className="col-span-12 md:col-span-7">
          <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-primary">
            // THE PROMISE
          </div>
          <h2 className="mt-3 font-display text-5xl font-extrabold tracking-tight text-white">
            <TextType
              text="Documents In. Intelligence Out."
              as="span"
              typingSpeed={60}
              showCursor={true}
              cursorCharacter="|"
              cursorClassName="text-primary"
              loop={false}
              startOnVisible={true}
              variableSpeed={{ min: 40, max: 90 }}
            />
          </h2>
          <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-white/50">
            CADIS processes any PDF through six sequential neural modules —
            entity extraction, ambiguity resolution, semantic search, and more
            — entirely on your machine.
          </p>
          <div className="mt-6 font-display text-xl font-semibold text-white/90">
            Multi-Dimensional Semantic Vectorization
          </div>
          <div className="mt-4 flex items-center gap-3">
            <div className="h-14 w-20 rounded-lg bg-white/[0.03] border border-white/[0.06]" />
            <div className="h-14 w-20 rounded-lg bg-primary/10 border border-primary/20" />
          </div>
        </div>
        <div className="col-span-12 md:col-span-5 grid grid-cols-2 gap-4">
          <div className="p-5">
            <div className="font-display text-4xl font-extrabold text-primary">
              <CountUp from={0} to={0.4} duration={1.5} separator="" className="font-display text-4xl font-extrabold" />s
            </div>
            <div className="mt-1 font-mono text-[10px] tracking-widest text-white/40">
              LATENCY PER PAGE
            </div>
          </div>
          <div className="p-5">
            <div className="font-display text-4xl font-extrabold text-[#34d399]">
              <CountUp from={0} to={99.8} duration={2} separator="," className="font-display text-4xl font-extrabold" />%
            </div>
            <div className="mt-1 font-mono text-[10px] tracking-widest text-white/40">
              RECALL @ TOP-K
            </div>
          </div>
          <div className="p-5 col-span-2">
            <div className="font-display text-2xl font-bold text-white">
              <CountUp from={0} to={12847} duration={2} separator="," className="font-display text-2xl font-bold" /> tokens
            </div>
            <div className="mt-1 font-mono text-[10px] tracking-widest text-white/40">
              PROCESSED · LAST SESSION
            </div>
          </div>
        </div>
      </section>

      {/* DIVIDER */}
      <div className="mt-24 mx-10 h-px bg-white/[0.06]" />

      {/* PRIVACY */}
      <section className="mt-24 grid grid-cols-12 gap-6 px-10 items-center">
        <div className="col-span-12 md:col-span-8">
          <h2 className="font-display text-4xl md:text-5xl font-extrabold tracking-tight text-white text-center md:text-left">
            <TextType
              text={["Your Data Never Leaves. Your Insights Always Arrive."]}
              as="span"
              typingSpeed={50}
              showCursor={true}
              cursorCharacter="|"
              cursorClassName="text-primary"
              loop={false}
              startOnVisible={true}
              variableSpeed={{ min: 30, max: 80 }}
            />
          </h2>
          <div className="mt-6 flex flex-wrap gap-3 justify-center md:justify-start">
            {[
              { l: "SOC2 Type II", icon: Shield },
              { l: "HIPAA Compliant", icon: Lock },
              { l: "GDPR Ready", icon: CheckCircle2 },
            ].map((s) => (
              <span
                key={s.l}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/[0.06] font-mono text-[11px] text-white/70"
              >
                <s.icon className="h-3.5 w-3.5 text-primary" />
                {s.l}
              </span>
            ))}
          </div>
        </div>
        <div className="col-span-12 md:col-span-4">
          <div className="p-5">
            <div className="flex items-center gap-2 font-mono text-[11px] text-white/40">
              <Cpu className="h-3.5 w-3.5 text-primary" /> ON-DEVICE INFERENCE
            </div>
            <div className="mt-2 text-[14px] text-white/70 leading-relaxed">
              Every model runs in your sandbox. Nothing is uploaded, logged, or
              retained.
            </div>
          </div>
        </div>
      </section>

      {/* DIVIDER */}
      <div className="mt-24 mx-10 h-px bg-white/[0.06]" />

      {/* PIPELINE */}
      <section className="mt-24 px-10">
        <div className="grid grid-cols-12 gap-8 items-center">
          <div className="col-span-12 md:col-span-5">
            <div
              className="rounded-xl text-white p-5 font-mono text-[12px] leading-relaxed border border-white/[0.06]"
              style={{ background: "rgba(255,255,255,0.02)" }}
            >
              <div className="text-white/30">$ cadis run paper.pdf</div>
              <div className="text-emerald-400">
                ✓ MOD-01 tokenized · 12,847 tk
              </div>
              <div className="text-emerald-400">
                ✓ MOD-02 embedded · 642 vec
              </div>
              <div className="text-emerald-400">
                ✓ MOD-03 entities · 46 spans
              </div>
              <div className="text-emerald-400">
                ✓ MOD-04 ambiguity resolved
              </div>
              <div className="text-emerald-400">✓ MOD-05 QA ready</div>
              <div className="text-emerald-400">
                ✓ MOD-06 summary 84% comp.
              </div>
              <div className="text-white/30">→ done in 2.4s</div>
            </div>
          </div>
          <div className="col-span-12 md:col-span-7">
            <h2 className="font-display text-3xl font-extrabold tracking-tight text-white">
              <TextType
                text="Seamless Semantic Pipeline"
                as="span"
                typingSpeed={55}
                showCursor={true}
                cursorCharacter="|"
                cursorClassName="text-primary"
                loop={false}
                startOnVisible={true}
                variableSpeed={{ min: 35, max: 85 }}
              />
            </h2>
            <p className="mt-2 text-[14px] text-white/50 max-w-xl">
              Watch your document transform across six neural stages — from raw
              tokens to executive summary — without ever leaving your machine.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                [
                  "Automated Tokenizing",
                  "spaCy en_core_web_trf with hybrid lemma normalization.",
                ],
                [
                  "Cross-Document Linking",
                  "BERT-NER spans merged across paragraph contexts.",
                ],
                [
                  "Confidence-Scored Output",
                  "Every answer grounded with character provenance.",
                ],
              ].map(([h, p]) => (
                <li key={h} className="flex gap-3">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <div>
                    <div className="font-display text-[14px] font-semibold text-white/90">
                      {h}
                    </div>
                    <div className="text-[13px] text-white/40">{p}</div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <PageFooter />
    </div>
  );
}
