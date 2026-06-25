import { Link } from "react-router-dom";
import { Upload, ArrowRight } from "lucide-react";

export default function NoDocument() {
  return (
    <div className="flex flex-col items-center justify-center py-32 px-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-6">
        <Upload className="h-7 w-7 text-primary" />
      </div>
      <h2 className="font-display text-2xl font-extrabold text-white mb-2">
        No Document Loaded
      </h2>
      <p className="text-white/40 text-sm max-w-sm mb-6">
        Upload a PDF or select a sample document to see real analysis results on this page.
      </p>
      <Link
        to="/analyze"
        className="cursor-target inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-white text-sm font-medium hover:translate-y-[-1px] transition shadow-lg shadow-primary/30"
      >
        Go to Analyze <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
