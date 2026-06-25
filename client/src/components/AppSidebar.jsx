import { Link, useLocation } from "react-router-dom";
import {
  LayoutGrid,
  FlaskConical,
  Cloud,
  History,
  Settings,
  Plus,
  FileText,
  HelpCircle,
  Beaker,
} from "lucide-react";

const primary = [
  { to: "/", label: "Overview", icon: LayoutGrid },
  { to: "/module-1", label: "Analysis", icon: FlaskConical, group: "analysis" },
  { to: "#", label: "Cloud Compute", icon: Cloud },
  { to: "#", label: "History", icon: History },
  { to: "#", label: "Settings", icon: Settings },
];

const secondary = [
  { label: "Documentation", icon: FileText },
  { label: "Support", icon: HelpCircle },
];

export default function AppSidebar() {
  const { pathname } = useLocation();
  const inAnalysis = pathname.startsWith("/module-");

  return (
    <aside className="hidden lg:flex fixed left-0 top-14 bottom-0 z-30 w-64 flex-col border-r border-border bg-sidebar">
      <div className="px-6 pt-6 pb-5">
        <div className="flex items-center gap-2">
          <Beaker className="h-4 w-4 text-foreground" />
          <span className="font-display text-[15px] font-semibold tracking-tight text-foreground">
            Research Suite
          </span>
        </div>
        <div className="mt-1 font-mono text-[10px] tracking-widest text-muted-foreground">
          V2.4.0-ALPHA
        </div>
      </div>

      <div className="px-4">
        <button className="cursor-target w-full h-10 rounded-lg bg-foreground text-background font-medium text-[13px] inline-flex items-center justify-center gap-2 hover:bg-foreground/90 transition">
          <Plus className="h-4 w-4" />
          New Experiment
        </button>
      </div>

      <nav className="mt-6 px-3 flex-1 overflow-y-auto">
        {primary.map((item) => {
          const Icon = item.icon;
          const isActive =
            (item.to === "/" && pathname === "/") ||
            (item.group === "analysis" && inAnalysis);

          if (item.to === "#") {
            return (
              <button
                key={item.label}
                className="w-full text-left h-10 px-3 rounded-lg flex items-center gap-3 text-[13px] text-muted-foreground hover:bg-muted hover:text-foreground transition"
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          }

          return (
            <Link
              key={item.label}
              to={item.to}
              className={[
                "h-10 px-3 rounded-lg flex items-center gap-3 text-[13px] transition",
                isActive
                  ? "bg-accent text-primary font-medium"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              ].join(" ")}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 pb-6 border-t border-border pt-4">
        {secondary.map((s) => {
          const Icon = s.icon;
          return (
            <button
              key={s.label}
              className="w-full text-left h-9 px-3 rounded-lg flex items-center gap-3 text-[13px] text-muted-foreground hover:text-foreground hover:bg-muted transition"
            >
              <Icon className="h-4 w-4" />
              {s.label}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
