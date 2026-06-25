export default function PageFooter() {
  return (
    <footer className="mt-16 -mx-8 px-8 pt-6 pb-6 border-t border-border flex flex-wrap items-center justify-between gap-3 text-[12px] text-muted-foreground">
      <span>&copy; 2024 CADIS Research Systems. All rights reserved.</span>
      <div className="flex items-center gap-5">
        <a href="#" className="hover:text-foreground transition">Legal</a>
        <a href="#" className="hover:text-foreground transition">Privacy</a>
        <a href="#" className="hover:text-foreground transition">API Docs</a>
        <a href="#" className="hover:text-foreground transition">Status</a>
      </div>
    </footer>
  );
}
