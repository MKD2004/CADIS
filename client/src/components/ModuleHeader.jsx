import { ChevronRight } from "lucide-react";
import PipelineProgress from "./PipelineProgress";
import DecryptedText from "./DecryptedText";

export default function ModuleHeader({ code, title, subtitle, badge, current }) {
  return (
    <div className="animate-float-up">
      <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
        <span className="hover:text-foreground transition cursor-pointer">Analysis</span>
        <ChevronRight className="h-3.5 w-3.5" />
        <span className="text-primary font-medium">
          {code} | {title.split(" — ")[0].split(" Engine")[0]}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <h1 className="font-display text-[34px] md:text-[40px] leading-tight font-bold tracking-tight text-foreground">
          <DecryptedText text={title} animateOn="view" speed={35} maxIterations={15} revealDirection="start" sequential />
        </h1>
        {badge && (
          <span className="px-2.5 py-1 text-[10px] font-mono uppercase tracking-widest rounded-full bg-accent text-accent-foreground border border-primary/20">
            {badge}
          </span>
        )}
      </div>
      <p className="mt-2 max-w-3xl text-[14px] leading-6 text-muted-foreground">{subtitle}</p>
      <div className="mt-5">
        <PipelineProgress current={current} />
      </div>
    </div>
  );
}
