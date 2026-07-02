import React, { Component, ErrorInfo, ReactNode } from "react";
import { ShieldAlert } from "lucide-react";

interface Props {
  children?: ReactNode;
  title?: string;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an unhandled rendering crash:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/10 p-6 text-slate-100 backdrop-blur-xl">
          <div className="flex items-center gap-3 mb-3 text-rose-400">
            <ShieldAlert className="h-6 w-6" />
            <h3 className="font-bold text-sm uppercase tracking-wider">{this.props.title || "Widget unavailable"}</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            An unexpected error occurred while rendering this interface component. Other dashboard elements remain active.
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs font-semibold transition-colors border border-rose-500/30"
          >
            Attempt Reload
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
