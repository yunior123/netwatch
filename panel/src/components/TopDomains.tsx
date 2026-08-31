"use client";

import { useMemo, useState } from "react";
import { MergedDevice } from "@/lib/types";

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

interface DomainEntry {
  domain: string;
  count: number;
  kinds: Record<string, number>;
  devs: Record<string, number>;
  last: number;
}

function kindBadge(kind: string): string {
  switch (kind) {
    case "dns": return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    case "tls": return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
    case "mdns": return "bg-pink-500/20 text-pink-400 border-pink-500/30";
    default: return "bg-slate-500/20 text-slate-400 border-slate-500/30";
  }
}

function fmtAgo(t: number): string {
  if (!t) return "—";
  const d = Date.now() / 1000 - t;
  if (d < 60) return `${d.toFixed(0)}s ago`;
  if (d < 3600) return `${(d / 60).toFixed(0)}m ago`;
  return `${(d / 3600).toFixed(1)}h ago`;
}

interface TopDomainsProps {
  domains: Record<string, { count: number; kinds: Record<string, number>; devs: Record<string, number>; last: number }>;
  filter: string;
  devices: MergedDevice[];
}

export default function TopDomains({ domains, filter, devices }: TopDomainsProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const deviceMap = useMemo(() => {
    const map = new Map<string, MergedDevice>();
    for (const d of devices) {
      map.set(d.ip, d);
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
          Object.keys(e.devs).some((d) => {
            const dev = deviceMap.get(d);
            return d.includes(q) || (dev?.hostname || "").toLowerCase().includes(q) || (dev?.vendor || "").toLowerCase().includes(q);
          })
      );
    }

    return filtered.sort((a, b) => b.count - a.count).slice(0, 30);
  }, [domains, filter, deviceMap]);

  const maxCount = sorted.length > 0 ? sorted[0].count : 1;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          URLs & Domains
        </h3>
        <span className="text-[10px] text-slate-600">{sorted.length} domains</span>
      </div>
      <div className="max-h-[500px] space-y-0.5 overflow-y-auto">
        {sorted.map((entry) => {
          const isExpanded = expanded === entry.domain;
          const deviceList = Object.entries(entry.devs)
            .sort(([, a], [, b]) => b - a)
            .map(([ip, count]) => {
              const dev = deviceMap.get(ip);
              return {
                ip,
                name: dev?.hostname || ip,
                vendor: dev?.vendor || "",
                type: dev ? (dev as MergedDevice & { activity_level?: string }).activity_level || "unknown" : "unknown",
                count,
              };
            });

          return (
            <div key={entry.domain} className="rounded-md transition-colors hover:bg-slate-800/30">
              <button
                onClick={() => setExpanded(isExpanded ? null : entry.domain)}
                className="flex w-full items-center gap-2 px-2 py-2 text-left"
              >
                <div className="min-w-0 flex-1">
                  {/* Domain name */}
                  <div className="text-sm font-medium text-slate-200 truncate">{formatDomain(entry.domain)}</div>
                  {/* Badges + device names inline */}
                  <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                    {Object.entries(entry.kinds).map(([k, n]) => (
                      <span key={k} className={`rounded border px-1 py-0.5 text-[9px] font-medium ${kindBadge(k)}`}>
                        {k.toUpperCase()} {n}
                      </span>
                    ))}
                    <span className="text-[10px] text-slate-500">•</span>
                    {deviceList.map((d) => (
                      <span key={d.ip} className="text-[10px] text-amber-400/80 font-mono">
                        {d.name}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <div className="h-2 w-16 overflow-hidden rounded bg-slate-800">
                    <div
                      className="h-full rounded bg-gradient-to-r from-cyan-600 to-blue-500 transition-all duration-500"
                      style={{ width: `${(entry.count / maxCount) * 100}%` }}
                    />
                  </div>
                  <span className="w-6 text-right font-mono text-[10px] text-slate-400">
                    {entry.count}
                  </span>
                  <span className="w-14 text-right text-[10px] text-slate-600">
                    {fmtAgo(entry.last)}
                  </span>
                </div>
              </button>

              {/* Expanded: full device breakdown */}
              {isExpanded && deviceList.length > 0 && (
                <div className="mx-2 mb-2 rounded border border-slate-700 bg-slate-900/80 px-3 py-2">
                  <div className="text-[10px] font-semibold uppercase text-slate-500 mb-1.5">
                    Devices accessing {formatDomain(entry.domain)}
                  </div>
                  <div className="space-y-1.5">
                    {deviceList.map((d) => (
                      <div key={d.ip} className="flex items-center gap-3 rounded bg-slate-800/50 px-2 py-1.5">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-baseline gap-2">
                            <span className="text-xs font-medium text-slate-200">{d.name}</span>
                            {d.vendor && <span className="text-[10px] text-cyan-400/60">{d.vendor}</span>}
                          </div>
                          <div className="font-mono text-[10px] text-slate-500">{d.ip}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono text-[10px] text-slate-400">{d.count}x</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      {sorted.length === 0 && (
        <div className="text-center text-xs text-slate-500 py-4">No domains captured yet</div>
      )}
    </div>
  );
}
