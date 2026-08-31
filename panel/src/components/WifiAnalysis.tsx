"use client";

import { useState, useEffect } from "react";

interface FilterPreset {
  key: string;
  label: string;
  filter: string;
  description: string;
}

interface TsharkRow {
  [key: string]: string;
}

interface TsharkResult {
  capture: string;
  filter: string;
  fields: string[];
  rows: TsharkRow[];
  truncated: boolean;
  error: string | null;
}

const DEFAULT_FILTERS: FilterPreset[] = [
  { key: "all", label: "All Wi-Fi", filter: "wlan", description: "Every 802.11 frame" },
  { key: "beacons", label: "Beacons", filter: "wlan.fc.type_subtype == 0x08", description: "AP advertising SSID" },
  { key: "probes_req", label: "Probes", filter: "wlan.fc.type_subtype == 0x04", description: "Clients searching" },
  { key: "deauth", label: "Deauth", filter: "wlan.fc.type_subtype == 0x0c", description: "Deauth attacks" },
  { key: "disassoc", label: "Disassoc", filter: "wlan.fc.type_subtype == 0x0a", description: "Disassociation" },
  { key: "auth", label: "Auth", filter: "wlan.fc.type_subtype == 0x0b", description: "Authentication" },
  { key: "assoc_req", label: "Assoc Req", filter: "wlan.fc.type_subtype == 0x00", description: "Join request" },
  { key: "assoc_resp", label: "Assoc Resp", filter: "wlan.fc.type_subtype == 0x01", description: "Join response" },
  { key: "eapol", label: "EAPOL", filter: "eapol", description: "WPA handshake" },
  { key: "data", label: "Data", filter: "wlan.fc.type == 0x02", description: "Traffic frames" },
  { key: "data_protected", label: "Encrypted", filter: "wlan.fc.type == 0x02 and wlan.fc.protected == 1", description: "Protected data" },
  { key: "retries", label: "Retries", filter: "wlan.fc.retry == 1", description: "Noisy clients" },
  { key: "dns", label: "DNS", filter: "dns", description: "DNS queries" },
  { key: "tls", label: "TLS", filter: "tls", description: "TLS traffic" },
  { key: "http", label: "HTTP", filter: "http", description: "HTTP traffic" },
  { key: "arp", label: "ARP", filter: "arp", description: "ARP requests" },
  { key: "icmp", label: "ICMP", filter: "icmp", description: "Ping/traceroute" },
  { key: "tcp_flags_syn", label: "SYN", filter: "tcp.flags.syn == 1 and tcp.flags.ack == 0", description: "New connections" },
  { key: "tcp_flags_rst", label: "RST", filter: "tcp.flags.reset == 1", description: "Connection resets" },
];

function fmtTime(epoch: string): string {
  if (!epoch) return "—";
  const d = new Date(parseFloat(epoch) * 1000);
  return d.toTimeString().slice(0, 8);
}

function kindColor(subtype: string): string {
  const s = subtype.toLowerCase();
  if (s.includes("0x08")) return "text-amber-400"; // beacon
  if (s.includes("0x04") || s.includes("0x05")) return "text-cyan-400"; // probe
  if (s.includes("0x0c") || s.includes("0x0a")) return "text-red-400"; // deauth/disassoc
  if (s.includes("0x0b")) return "text-emerald-400"; // auth
  if (s.includes("0x00") || s.includes("0x01")) return "text-blue-400"; // assoc
  return "text-slate-400";
}

interface WifiAnalysisProps {
  captures: { name: string; size: number; mtime: number }[];
  selectedCapture: string | null;
  onSelectCapture: (name: string) => void;
}

export default function WifiAnalysis({ captures, selectedCapture, onSelectCapture }: WifiAnalysisProps) {
  const [customFilter, setCustomFilter] = useState("");
  const [selectedFilter, setSelectedFilter] = useState("wlan");
  const [maxRows, setMaxRows] = useState(500);
  const [result, setResult] = useState<TsharkResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [quickCap, setQuickCap] = useState("");

  // Auto-run when capture selected + filter changes
  useEffect(() => {
    if (selectedCapture && selectedCapture !== quickCap) {
      setQuickCap(selectedCapture);
      runAnalysis(selectedCapture, customFilter.trim() || selectedFilter, maxRows);
    }
  }, [selectedCapture]);

  async function runAnalysis(cap?: string, filt?: string, rows?: number) {
    const capture = cap || selectedCapture;
    if (!capture) return;
    setLoading(true);
    try {
      const res = await fetch("/api/tshark", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          capture,
          display_filter: filt || customFilter.trim() || selectedFilter,
          max_rows: rows || maxRows,
        }),
      });
      setResult(await res.json());
    } catch {
      setResult({ capture: capture || "", filter: "", fields: [], rows: [], truncated: false, error: "Fetch failed" });
    }
    setLoading(false);
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]">
          <label className="mb-1 block text-[10px] text-slate-500">Custom Filter (Wireshark display filter)</label>
          <input
            type="text"
            value={customFilter}
            onChange={(e) => setCustomFilter(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runAnalysis()}
            placeholder='e.g. wlan.fc.type_subtype == 0x08 and wlan.ssid == "MyNet"'
            className="w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 font-mono text-xs text-slate-200 placeholder-slate-600"
          />
        </div>
        <div className="min-w-[100px]">
          <label className="mb-1 block text-[10px] text-slate-500">Max Rows</label>
          <input
            type="number" min={1} max={10000} value={maxRows}
            onChange={(e) => setMaxRows(parseInt(e.target.value) || 500)}
            className="w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-xs text-slate-200"
          />
        </div>
        <button
          onClick={() => runAnalysis()}
          disabled={loading || !selectedCapture}
          className="rounded bg-cyan-700 px-4 py-1.5 text-sm font-medium text-white hover:bg-cyan-600 disabled:opacity-50"
        >
          {loading ? "Running..." : "Run"}
        </button>
      </div>

      {/* Quick filter chips */}
      <div className="flex flex-wrap gap-1.5">
        {DEFAULT_FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => { setSelectedFilter(f.filter); setCustomFilter(""); if (selectedCapture) runAnalysis(selectedCapture, f.filter); }}
            className={`rounded px-2 py-0.5 text-[10px] transition-colors ${
              selectedFilter === f.filter && !customFilter
                ? "bg-cyan-700 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700"
            }`}
            title={f.description}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Results */}
      {result && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/50">
          <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
            <div className="flex items-center gap-2 overflow-hidden">
              <span className="text-[10px] text-slate-500">tshark</span>
              <code className="truncate rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-cyan-300">
                -r {result.capture} -Y &apos;{result.filter}&apos;
              </code>
            </div>
            <div className="flex shrink-0 items-center gap-2 text-xs">
              <span className="text-slate-400">{result.rows.length} rows</span>
              {result.truncated && <span className="text-amber-400">truncated</span>}
            </div>
          </div>

          {result.error && (
            <div className="border-b border-slate-800 bg-red-950/20 px-3 py-2 text-xs text-red-400">
              {result.error}
            </div>
          )}

          {result.rows.length > 0 ? (
            <div className="max-h-[600px] overflow-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 z-10 bg-slate-900">
                  <tr className="text-left text-slate-500">
                    {result.fields.map((f) => (
                      <th key={f} className="whitespace-nowrap px-2 py-1.5 font-medium">{f}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, i) => (
                    <tr key={i} className="border-t border-slate-800/50 hover:bg-slate-800/30">
                      {result.fields.map((f) => (
                        <td
                          key={f}
                          className={`max-w-[250px] truncate px-2 py-1 font-mono ${
                            f === "wlan.fc.type_subtype" ? kindColor(row[f]) :
                            f === "wlan.ssid" ? "text-cyan-300" :
                            f === "wlan.sa" || f === "wlan.da" ? "text-amber-300" :
                            "text-slate-300"
                          }`}
                          title={row[f]}
                        >
                          {f === "frame.time_epoch" ? fmtTime(row[f]) : row[f]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            !result.error && (
              <div className="p-8 text-center text-sm text-slate-500">
                {selectedCapture ? "No matches for this filter" : "Select a capture file to analyze"}
              </div>
            )
          )}
        </div>
      )}

      {!result && !loading && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-12 text-center text-sm text-slate-500">
          Select a capture file and filter to begin analysis
        </div>
      )}
    </div>
  );
}
