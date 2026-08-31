"use client";

import { useState, useRef } from "react";

interface Capture {
  name: string;
  size: number;
  mtime: number;
}

interface UploadResult {
  name?: string;
  size?: number;
  summary?: string;
  error?: string;
}

function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtAgo(ts: number): string {
  const d = Date.now() / 1000 - ts;
  if (d < 60) return `${d.toFixed(0)}s ago`;
  if (d < 3600) return `${(d / 60).toFixed(0)}m ago`;
  return `${(d / 3600).toFixed(1)}h ago`;
}

interface CaptureManagerProps {
  captures: Capture[];
  onRefresh: () => void;
  onSelect: (name: string) => void;
  selected: string | null;
}

export default function CaptureManager({ captures, onRefresh, onSelect, selected }: CaptureManagerProps) {
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);

    const fd = new FormData();
    fd.append("file", file);

    try {
      const res = await fetch("/api/captures", { method: "POST", body: fd });
      const data = await res.json();
      setUploadResult(data);
      onRefresh();
    } catch {
      setUploadResult({ error: "upload failed" });
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Capture Files ({captures.length})
        </h3>
        <div className="flex gap-2">
          <button
            onClick={onRefresh}
            className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400 hover:bg-slate-700"
          >
            Refresh
          </button>
          <label className="cursor-pointer rounded bg-cyan-700 px-2 py-1 text-xs text-white hover:bg-cyan-600">
            {uploading ? "Uploading..." : "Upload PCAP"}
            <input ref={fileRef} type="file" accept=".pcap,.pcapng,.cap" className="hidden" onChange={handleUpload} />
          </label>
        </div>
      </div>

      {uploadResult && (
        <div className={`mb-3 rounded px-2 py-1 text-xs ${uploadResult.error ? "bg-red-950/30 text-red-400" : "bg-emerald-950/30 text-emerald-400"}`}>
          {uploadResult.error || `Uploaded ${uploadResult.name} (${fmtBytes(uploadResult.size || 0)})`}
        </div>
      )}

      {captures.length === 0 ? (
        <div className="text-center text-sm text-slate-500">No capture files. Upload a .pcap/.pcapng/.cap file.</div>
      ) : (
        <div className="max-h-[300px] space-y-1 overflow-y-auto">
          {captures.map((c) => (
            <button
              key={c.name}
              onClick={() => onSelect(c.name)}
              className={`w-full rounded px-3 py-2 text-left text-xs transition-colors ${
                selected === c.name
                  ? "bg-cyan-900/30 border border-cyan-700/50"
                  : "hover:bg-slate-800 border border-transparent"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-200">{c.name}</span>
                <span className="text-slate-500">{fmtBytes(c.size)}</span>
              </div>
              <div className="text-[10px] text-slate-500">{fmtAgo(c.mtime)}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
