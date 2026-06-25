export default function CompletionStrip({ text, celebrate }) {
  return (
    <div
      className={["mt-10 surface-card p-4 flex items-center gap-3", celebrate ? "pulse-glow" : ""].join(" ")}
      style={{
        borderColor: "#34d39958",
        background: "linear-gradient(90deg, #34d39910, var(--card))",
      }}
    >
      <span className="grid place-items-center h-7 w-7 rounded-full bg-success/15 text-success font-bold text-sm">
        ✓
      </span>
      <span className="font-mono text-[12px] text-foreground/90">{text}</span>
    </div>
  );
}
