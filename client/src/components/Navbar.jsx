import { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Search, Activity, Github } from "lucide-react";
import { checkHealth } from "@/lib/api";
import PillNav from "./PillNav";

const navItems = [
  { label: "Home", href: "/" },
  { label: "Analyze", href: "/analyze" },
];

function HealthDot() {
  const [status, setStatus] = useState(null);
  const [showTooltip, setShowTooltip] = useState(false);

  useEffect(() => {
    let mounted = true;
    const check = () => {
      checkHealth()
        .then((d) => mounted && setStatus(d))
        .catch(() => mounted && setStatus({ status: "unreachable" }));
    };
    check();
    const interval = setInterval(check, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const isOk = status?.status === "ok" || status?.gateway === "ok";
  const isDegraded = status?.status === "degraded";
  const dotColor = isOk ? "bg-[#34d399]" : isDegraded ? "bg-[#fbbf24]" : "bg-red-400";
  const label = isOk ? "All systems operational" : isDegraded ? "Degraded — some models unavailable" : "Backend unreachable";

  const models = status?.ml_backend?.models || status?.models;

  return (
    <div className="relative">
      <button
        className="cursor-target h-9 w-9 grid place-items-center rounded-lg hover:bg-white/10 transition"
        aria-label="System health"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <Activity className="h-4 w-4 text-white/70" />
        <span className={`absolute top-1.5 right-1.5 w-2 h-2 rounded-full ${dotColor} ${isOk ? "" : "animate-pulse"}`} />
      </button>

      {showTooltip && (
        <div className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-white/[0.06] p-3 z-50" style={{ background: "#0d0d14" }}>
          <div className="flex items-center gap-2 mb-2">
            <span className={`w-2 h-2 rounded-full ${dotColor}`} />
            <span className="font-mono text-[10px] text-white/60 uppercase tracking-widest">{label}</span>
          </div>
          {models && (
            <div className="space-y-1 border-t border-white/[0.06] pt-2">
              {Object.entries(models).map(([name, ready]) => (
                <div key={name} className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-white/40 uppercase">{name}</span>
                  <span className={`font-mono text-[10px] ${ready ? "text-[#34d399]" : "text-red-400"}`}>
                    {ready ? "✓" : "✗"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SearchBar() {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const navigate = useNavigate();
  const inputRef = useRef(null);

  const routes = [
    ...navItems.map((item) => ({ label: item.label, href: item.href })),
    { label: "Preprocessing", href: "/module-1" },
    { label: "Embeddings", href: "/module-2" },
    { label: "NER + IE", href: "/module-3" },
    { label: "Ambiguity", href: "/module-4" },
    { label: "QA Engine", href: "/module-5" },
    { label: "Summary", href: "/module-6" },
  ];
  const filtered = query.trim()
    ? routes.filter((r) => r.label.toLowerCase().includes(query.toLowerCase()))
    : [];

  const handleSelect = (href) => {
    navigate(href);
    setQuery("");
    setFocused(false);
    inputRef.current?.blur();
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && filtered.length > 0) {
      handleSelect(filtered[0].href);
    }
    if (e.key === "Escape") {
      setQuery("");
      setFocused(false);
      inputRef.current?.blur();
    }
  };

  return (
    <div className="relative hidden md:block">
      <div className="flex items-center gap-2 h-9 w-64 px-3 rounded-lg border border-white/10 focus-within:border-primary/40 transition" style={{ background: "#0d0d14" }}>
        <Search className="h-4 w-4 text-white/50" />
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 150)}
          onKeyDown={handleKeyDown}
          placeholder="Search modules..."
          className="flex-1 bg-transparent outline-none text-[13px] text-white/90 placeholder:text-white/40"
        />
        <kbd className="hidden lg:inline font-mono text-[9px] text-white/20 border border-white/[0.06] rounded px-1 py-0.5">/</kbd>
      </div>

      {focused && filtered.length > 0 && (
        <div className="absolute top-full mt-1 left-0 w-full rounded-xl border border-white/[0.06] overflow-hidden z-50" style={{ background: "#0d0d14" }}>
          {filtered.map((r) => (
            <button
              key={r.href}
              onMouseDown={() => handleSelect(r.href)}
              className="w-full flex items-center gap-2 px-3 py-2 text-left text-sm text-white/70 hover:bg-white/5 hover:text-white transition-colors"
            >
              <Search className="h-3 w-3 text-white/30" />
              {r.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Navbar() {
  const { pathname } = useLocation();

  return (
    <header className="fixed top-0 inset-x-0 z-50 border-b border-white/10" style={{ background: "#000000" }}>
      <div className="h-14 px-5 flex items-center gap-6">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <span className="font-display text-[15px] font-extrabold tracking-tight text-white">CADIS</span>
        </Link>

        <PillNav
          logoAlt=""
          items={navItems}
          activeHref={pathname}
          baseColor="#0d0d14"
          pillColor="#1a1a28"
          hoveredPillTextColor="#298DFF"
          pillTextColor="#ffffff"
          initialLoadAnimation={true}
        />

        <div className="ml-auto flex items-center gap-3">
          <SearchBar />
          <HealthDot />
          <a
            href="https://github.com/MKD2004/CADIS"
            target="_blank"
            rel="noopener noreferrer"
            className="cursor-target h-9 w-9 grid place-items-center rounded-lg hover:bg-white/10 transition"
            aria-label="GitHub repository"
          >
            <Github className="h-4 w-4 text-white/70" />
          </a>
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-[#298DFF] to-[#22d3ee] ring-2 ring-white/20" />
        </div>
      </div>
    </header>
  );
}
