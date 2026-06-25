import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";

export default function ModuleNav({ prev, next, prevLabel, nextLabel }) {
  return (
    <div className="mt-16 grid grid-cols-2 gap-4">
      {prev ? (
        <Link
          to={prev.to}
          className="cursor-target surface-card group p-5 flex items-center gap-4 hover:border-primary/40 hover:shadow-md transition"
        >
          <ArrowLeft className="h-5 w-5 text-primary group-hover:-translate-x-1 transition" />
          <div className="text-left">
            <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {prevLabel ?? "Previous"}
            </div>
            <div className="font-display text-[15px] font-semibold text-foreground">
              {prev.label}
            </div>
          </div>
        </Link>
      ) : (
        <div />
      )}
      {next ? (
        <Link
          to={next.to}
          className="cursor-target surface-card group p-5 flex items-center justify-end gap-4 text-right hover:border-primary/40 hover:shadow-md transition"
        >
          <div>
            <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {nextLabel ?? "Next"}
            </div>
            <div className="font-display text-[15px] font-semibold text-foreground">
              {next.label}
            </div>
          </div>
          <ArrowRight className="h-5 w-5 text-primary group-hover:translate-x-1 transition" />
        </Link>
      ) : (
        <div />
      )}
    </div>
  );
}
