import { Link } from "react-router-dom";

const modules = [
  { n: 1, to: "/module-1", label: "Preprocessing" },
  { n: 2, to: "/module-2", label: "Embeddings" },
  { n: 3, to: "/module-3", label: "NER + IE" },
  { n: 4, to: "/module-4", label: "Ambiguity" },
  { n: 5, to: "/module-5", label: "QA" },
  { n: 6, to: "/module-6", label: "Summary" },
];

export default function PipelineProgress({ current }) {
  return (
    <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
      {modules.map((m, i) => {
        const done = m.n < current;
        const active = m.n === current;
        return (
          <div key={m.n} className="flex items-center gap-2">
            <Link
              to={m.to}
              className={[
                "h-6 w-6 grid place-items-center rounded-full text-[10px] font-medium border transition",
                active
                  ? "bg-primary text-primary-foreground border-primary"
                  : done
                  ? "bg-primary/10 text-primary border-primary/30"
                  : "bg-background text-muted-foreground border-border hover:border-primary/40",
              ].join(" ")}
              title={`MOD-0${m.n} · ${m.label}`}
            >
              {m.n}
            </Link>
            {i < modules.length - 1 && (
              <span
                className={["h-px w-6", done ? "bg-primary/40" : "bg-border"].join(" ")}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
