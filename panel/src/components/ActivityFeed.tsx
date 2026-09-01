"use client";

import { useState } from "react";
import { TrafficEvent, MergedDevice } from "@/lib/types";
import NimAnalysis from "./NimAnalysis";

function fmtTime(t: number): string {
  if (!t) return "—";
  return new Date(t * 1000).toTimeString().slice(0, 8);
}

function formatDomain(domain: string): string {
  let d = domain.replace(/\.$/, "");
  if (d.endsWith(".local")) return d;
  if (d.endsWith(".in-addr.arpa")) {
    const parts = d.replace(".in-addr.arpa", "").split(".").reverse();
    return parts.join(".");
  }
  if (d.startsWith("_") && d.includes("._")) {
    const match = d.match(/_([^._]+\.[^._]+)\.local/);
    if (match) return match[1] + ".local";
  }
  return d;
}

function kindStyle(kind: string): string {
  switch (kind) {
    case "dns": return "bg-blue-950 text-blue-300 border border-blue-900/50";
    case "tls": return "bg-emerald-950 text-emerald-300 border border-emerald-900/50";
    case "mdns": return "bg-pink-950 text-pink-300 border border-pink-900/50";
    case "http": return "bg-amber-950 text-amber-300 border border-amber-900/50";
    default: return "bg-slate-800 text-slate-400 border border-slate-700";
  }
}

function deviceIcon(dev?: MergedDevice): string {
  if (!dev) return "📡";
  if (dev.device_icon && dev.device_icon !== "📡") return dev.device_icon;
  const h = (dev.hostname || "").toLowerCase();
  if (h.includes("iphone") || h.includes("ipad") || h.includes("phone")) return "📱";
  if (h.includes("macbook") || h.includes("mac")) return "💻";
  if (h.includes("tv") || h.includes("roku") || h.includes("firestick")) return "📺";
  if (h.includes("watch")) return "⌚";
  if (h.includes("thermostat")) return "🌡️";
  if (h.includes("camera")) return "📷";
  if (h.includes("printer")) return "🖨️";
  if (h.includes("router") || h.includes("gateway")) return "🌐";
  return "📡";
}

function deviceName(dev?: MergedDevice): string {
  if (!dev) return "";
  if (dev.device_model && dev.device_model !== "Unknown Device") return dev.device_model;
  if (dev.hostname && dev.hostname !== "?" && !dev.hostname.match(/^[\d:a-f]{17}$/i)) return dev.hostname;
  return dev.vendor || "";
}

interface ActivityFeedProps {
  events: TrafficEvent[];
  filter: string;
  devices?: MergedDevice[];
}

export default function ActivityFeed({ events, filter, devices }: ActivityFeedProps) {
  const [analyzeTarget, setAnalyzeTarget] = useState<string | null>(null);
  const deviceMap = new Map<string, MergedDevice>();
  if (devices) {
    for (const d of devices) {
      deviceMap.set(d.ip, d);
    }
  }

  const filtered = events.filter((e) => {
    if (!filter) return true;
    const q = filter.toLowerCase();
    const dev = deviceMap.get(e.dev);
    const name = dev ? deviceName(dev).toLowerCase() : "";
    return e.host.toLowerCase().includes(q) || e.dev.toLowerCase().includes(q) || e.kind.includes(q) || name.includes(q);
  });

  const display = filtered.slice().reverse().slice(0, 200);

  if (display.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-500">
        Waiting for packets...
      </div>
    );
  }

  return (
    <>
      {analyzeTarget && (
        <NimAnalysis domain={analyzeTarget} onClose={() => setAnalyzeTarget(null)} />
      )}
      <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900/50">
        <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Live Events
          </h3>
          <span className="text-[10px] text-slate-600">
            {filtered.length} / {events.length}
          </span>
        </div>
        <div className="max-h-[500px] overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-slate-900">
              <tr className="text-left text-slate-500">
                <th className="px-3 py-1.5 font-medium">Time</th>
                <th className="px-3 py-1.5 font-medium">Kind</th>
                <th className="px-3 py-1.5 font-medium">Host</th>
                <th className="px-3 py-1.5 font-medium">Device</th>
                <th className="px-2 py-1.5 font-medium w-8"></th>
              </tr>
            </thead>
            <tbody>
              {display.map((e, i) => {
                const dev = deviceMap.get(e.dev);
                const icon = deviceIcon(dev);
                const name = deviceName(dev);
                return (
                  <tr
                    key={`${e.t}-${e.host}-${i}`}
                    className="border-t border-slate-800/50 hover:bg-slate-800/30 group"
                  >
                    <td className="whitespace-nowrap px-3 py-1 font-mono text-slate-500">
                      {fmtTime(e.t)}
                    </td>
                    <td className="px-3 py-1">
                      <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ${kindStyle(e.kind)}`}>
                        {e.kind}
                      </span>
                    </td>
                    <td className="max-w-[200px] truncate px-3 py-1 font-medium text-cyan-300">
                      {formatDomain(e.host)}
                    </td>
                    <td className="max-w-[160px] truncate px-3 py-1 text-slate-400">
                      <span className="mr-1">{icon}</span>
                      {name || e.dev}
                      {name && <span className="ml-1 text-[10px] text-slate-600">{e.dev}</span>}
                    </td>
                    <td className="px-2 py-1">
                      <button
                        onClick={() => setAnalyzeTarget(formatDomain(e.host))}
                        title="NIM Security Check"
                        className="opacity-0 group-hover:opacity-100 transition-opacity text-cyan-500 hover:text-cyan-300 text-sm"
                      >
                        🛡️
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
