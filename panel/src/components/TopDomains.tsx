"use client";

import { useMemo, useState } from "react";
import { MergedDevice } from "@/lib/types";

interface DomainEntry {
  domain: string;
  count: number;
  kinds: Record<string, number>;
  devs: Record<string, number>;
  last: number;
}

function kindBadge(kind: string): string {
  switch (kind) {
    case "dns": return "bg-blue-500/20 text-blue-400";
    case "tls": return "bg-emerald-500/20 text-emerald-400";
    case "mdns": return "bg-pink-500/20 text-pink-400";
    default: return "bg-slate-500/20 text-slate-400";
  }
}

function fmtAgo(t: number): string {
  if (!t) return "—";
  const d = Date.now() / 1000 - t;
  if (d < 60) return `${d.toFixed(0)}s`;
  if (d < 3600) return `${(d / 60).toFixed(0)}m`;
  return `${(d / 3600).toFixed(1)}h`;
}

interface TopDomainsProps {
  domains: Record<string, { count: number; kinds: Record<string, number>; devs: Record<string, number>; last: number }>;
  filter: string;
  devices: MergedDevice[];
}

export default function TopDomains({ domains, filter, devices }: TopDomainsProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const deviceNameMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const d of devices) {
      map.set(d.ip, d.hostname || d.ip);
    }
    return map;
  }, [devices]);

  const sorted = useMemo(() => {
    const entries: DomainEntry[] = Object.entries(domains).map(([domain, info]) => ({
      domain,
      count: info.count,
      kinds: info.kinds || {},
      devs: info.devs || {},
      last: info.last || 0,
    }));

    let filtered = entries;
    if (filter) {
      const q = filter.toLowerCase();
      filtered = entries.filter(
        (e) =>
          e.domain.toLowerCase().includes(q) ||
          Object.keys(e.devs).some((d) => d.includes(q) || (deviceNameMap.get(d) || "").toLowerCase().includes(q))
      );
    }

    return filtered.sort((a, b) => b.count - a.count).slice(0, 25);
  }, [domains, filter, deviceNameMap]);

  const maxCount = sorted.length > 0 ? sorted[0].count : 1;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Top Domains
        </h3>
        <span className="text-[10px] text-slate-600">{sorted.length}</span>
      </div>
      <div className="max-h-[400px] space-y-1 overflow-y-auto">
        {sorted.map((entry) => {
          const isExpanded = expanded === entry.domain;
          const deviceList = Object.entries(entry.devs)
            .sort(([, a], [, b]) => b - a)
            .map(([ip, count]) => ({
              ip,
              name: deviceNameMap.get(ip) || ip,
              count,
            }));

          return (
            <div key={entry.domain}>
              <button
                onClick={() => setExpanded(isExpanded ? null : entry.domain)}
                className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left transition-colors hover:bg-slate-800/50"
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm text-slate-200">{entry.domain}</div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    {Object.entries(entry.kinds).map(([k, n]) => (
                      <span key={k} className={`rounded px-1 py-0.5 text-[9px] font-medium ${kindBadge(k)}`}>
                        {k} {n}
                      </span>
                    ))}
                    {/* Show device names inline */}
                    <span className="text-[10px] text-slate-500">
                      {deviceList.map((d) => d.name).join(", ")}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-20 overflow-hidden rounded bg-slate-800">
                    <div
                      className="h-full rounded bg-gradient-to-r from-cyan-600 to-blue-500 transition-all duration-500"
                      style={{ width: `${(entry.count / maxCount) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right font-mono text-[10px] text-slate-500">
                    {entry.count}
                  </span>
                  <span className="w-8 text-right text-[10px] text-slate-600">
                    {fmtAgo(entry.last)}
                  </span>
                </div>
              </button>

              {/* Expanded: show devices that visited this domain */}
              {isExpanded && deviceList.length > 0 && (
                <div className="ml-4 mb-1 rounded border border-slate-800 bg-slate-900/80 px-3 py-2">
                  <div className="text-[10px] font-semibold uppercase text-slate-500 mb-1">Devices</div>
                  {deviceList.map((d) => (
                    <div key={d.ip} className="flex items-center gap-2 text-xs">
                      <span className="font-mono text-amber-300">{d.name}</span>
                      <span className="text-slate-600">{d.ip}</span>
                      <span className="ml-auto font-mono text-[10px] text-slate-500">{d.count}x</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
