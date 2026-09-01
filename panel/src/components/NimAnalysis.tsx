"use client";

import { useState, useEffect } from "react";

interface NimAnalysisProps {
  domain?: string;
  device?: Record<string, unknown>;
  events?: Array<{ t: number; dev: string; kind: string; host: string; service?: string }>;
  onClose?: () => void;
}

const DEFAULT_MODELS = [
  "deepseek-ai/deepseek-v4-flash-0731",
  "google/gemma-4-31b-it",
  "deepseek-ai/deepseek-v4-pro-0813",
  "meta/llama-3.1-8b-instruct",
];

export default function NimAnalysis({ domain, device, events, onClose }: NimAnalysisProps) {
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState(DEFAULT_MODELS[0]);
  const [availableModels, setAvailableModels] = useState<string[]>(DEFAULT_MODELS);
  const [tokens, setTokens] = useState<Record<string, number> | null>(null);

  useEffect(() => {
    fetch("/api/nim-models")
      .then((r) => r.json())
      .then((d) => {
        if (d.models?.length > 0) setAvailableModels(d.models);
      })
      .catch(() => {});
  }, []);

  const analyze = async () => {
    setLoading(true);
    setError(null);
    setAnalysis(null);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain, device, events, model }),
      });
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setAnalysis(data.analysis);
        setTokens(data.tokens);
      }
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-xl border border-slate-700 bg-slate-900 p-5 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-cyan-400">
            🛡️ NIM Security Analysis
          </h3>
          {onClose && (
            <button onClick={onClose} className="text-slate-500 hover:text-white text-xl">×</button>
          )}
        </div>

        {domain && (
          <div className="mb-3 text-sm text-slate-400">
            Target: <span className="text-cyan-300 font-mono">{domain}</span>
          </div>
        )}
        {device && !domain && (
          <div className="mb-3 text-sm text-slate-400">
            Device: <span className="text-cyan-300">{(device as Record<string, unknown>).device_model as string || (device as Record<string, unknown>).hostname as string || (device as Record<string, unknown>).ip as string}</span>
          </div>
        )}

        <div className="mb-4 flex items-center gap-3">
          <label className="text-xs text-slate-500">Model:</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 focus:border-cyan-500 focus:outline-none"
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <button
            onClick={analyze}
            disabled={loading}
            className="rounded-lg bg-cyan-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Analyzing..." : "Analyze"}
          </button>
        </div>

        {loading && (
          <div className="flex items-center gap-2 py-8 text-cyan-400">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Calling {model.split("/").pop()}...
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-800 bg-red-950/50 p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {analysis && (
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <pre className="whitespace-pre-wrap text-sm text-slate-200 leading-relaxed">{analysis}</pre>
            {tokens && (
              <div className="mt-3 pt-2 border-t border-slate-700 text-[10px] text-slate-600">
                Tokens: {tokens.total_tokens || "?"} | Model: {model.split("/").pop()}
              </div>
            )}
          </div>
        )}

        {!loading && !analysis && !error && (
          <div className="py-6 text-center text-sm text-slate-600">
            Select a model and click Analyze to check for threats
          </div>
        )}
      </div>
    </div>
  );
}
