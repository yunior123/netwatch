"use client";

import { useState } from "react";
import { DomainInfo } from "@/lib/types";

function fmtAgo(t: number): string {
  if (!t) return "never";
  const d = Date.now() / 1000 - t;
  if (d < 5) return "now";
  if (d < 60) return `${d.toFixed(0)}s`;
  if (d < 3600) return `${(d / 60).toFixed(0)}m`;
  return `${(d / 3600).toFixed(1)}h`;
}

function kindDot(kind: string): string {
  switch (kind) {
    case "dns": return "bg-blue-400";
    case "tls": return "bg-emerald-400";
    case "mdns": return "bg-pink-400";
    default: return "bg-slate-500";
  }
}

interface TopDomainsProps {
  domains: Record<string, DomainInfo>;
  filter: string;
}

export default function TopDomains({ domains, filter }: TopDomainsProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  const entries = Object.entries(domains)
    .filter(([k]) => {
      if (!filter) return true;
      return k.toLowerCase().includes(filter.toLowerCase());
    })
    .sort(([, a], [, b]) => b.count - a.count)
    .slice(0, 60);

  const maxCount = entries.length > 0 ? entries[0][1].count : 1;

  if (entries.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-500">
        No domains yet
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-900/50">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Top Domains
        </h3>
        <span className="text-[10px] text-slate-600">{entries.length}</span>
      </div>
      <div className="max-h-[400px] overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-slate-900">
            <tr className="text-left text-slate-500">
              <th className="px-3 py-1.5 font-medium">Domain</th>
              <th className="px-3 py-1.5 text-right font-medium">Count</th>
              <th className="px-3 py-1.5 font-medium">Last</th>
              <th className="px-3 py-1.5 font-medium">Types</th>
              <th className="px-3 py-1.5 font-medium w-24"></th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([domain, info]) => {
              const pct = Math.round((info.count / maxCount) * 100);
              const isExpanded = expanded === domain;
              return (
                <>
                  <tr
                    key={domain}
                    className="cursor-pointer border-t border-slate-800/50 hover:bg-slate-800/30"
                    onClick={() => setExpanded(isExpanded ? null : domain)}
                  >
                    <td className="max-w-[200px] truncate px-3 py-1.5 font-medium text-cyan-300">
                      {domain}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-slate-300">
                      {info.count}
                    </td>
                    <td className="whitespace-nowrap px-3 py-1.5 text-slate-500">
                      {fmtAgo(info.last)}
                    </td>
                    <td className="px-3 py-1.5">
                      <div className="flex gap-1">
                        {Object.entries(info.kinds).map(([k, n]) => (
                          <span key={k} className="flex items-center gap-1">
                            <span className={`h-1.5 w-1.5 rounded-full ${kindDot(k)}`} />
                            <span className="text-slate-500">{n}</span>
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-1.5">
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${domain}-detail`} className="border-t border-slate-800/50 bg-slate-800/20">
                      <td colSpan={5} className="px-3 py-2">
                        <div className="mb-2 text-[10px] text-slate-500">
                          First: {fmtAgo(info.first)} &middot; Last: {fmtAgo(info.last)} &middot; Total: {info.count}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(info.devs)
                            .sort(([, a], [, b]) => b - a)
                            .map(([dev, count]) => (
                              <span
                                key={dev}
                                className="inline-block rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400"
                              >
                                {dev} ({count})
                              </span>
                            ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
