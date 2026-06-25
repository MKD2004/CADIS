import { Component } from "react";
import { AlertTriangle, RotateCcw, RefreshCw } from "lucide-react";

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("[CADIS ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="min-h-screen flex items-center justify-center bg-void px-4">
        <div className="max-w-md w-full text-center">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-6">
            <AlertTriangle size={28} className="text-red-400" />
          </div>

          <h1 className="font-display text-2xl font-700 text-white mb-2">
            Something went wrong
          </h1>
          <p className="font-body text-sm text-slate-400 mb-8">
            The AI backend may have returned an unexpected response
          </p>

          {this.state.error && (
            <div className="mb-6 px-4 py-3 rounded-xl bg-slate-800/40 border border-glass text-left">
              <p className="font-mono text-xs text-red-400/80 break-words">
                {this.state.error.message}
              </p>
            </div>
          )}

          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="
                flex items-center gap-2 px-5 py-2.5 rounded-xl
                bg-signal-500/10 border border-signal-500/30
                font-body text-sm text-signal-300
                hover:bg-signal-500/20 hover:border-signal-500/50
                transition-colors duration-200
              "
            >
              <RotateCcw size={14} />
              Try again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="
                flex items-center gap-2 px-5 py-2.5 rounded-xl
                border border-glass-bright
                font-body text-sm text-slate-400
                hover:border-white/20 hover:text-slate-300
                transition-colors duration-200
              "
            >
              <RefreshCw size={14} />
              Refresh page
            </button>
          </div>
        </div>
      </div>
    );
  }
}

export class PanelErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error(`[CADIS Panel: ${this.props.name || "unknown"}]`, error, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="glass-bright rounded-2xl p-5 border border-glass-bright shadow-glass">
        <div className="flex items-center gap-3 text-left">
          <div className="w-9 h-9 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center flex-shrink-0">
            <AlertTriangle size={16} className="text-red-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-body text-sm text-slate-300">
              {this.props.name || "This panel"} failed to render
            </p>
            <p className="font-mono text-xs text-slate-500 mt-0.5">
              Other panels are unaffected
            </p>
          </div>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="
              flex items-center gap-1.5 px-3 py-1.5 rounded-lg
              bg-signal-500/10 border border-signal-500/20
              font-mono text-xs text-signal-400
              hover:bg-signal-500/20 transition-colors flex-shrink-0
            "
          >
            <RotateCcw size={12} />
            Retry
          </button>
        </div>
      </div>
    );
  }
}
