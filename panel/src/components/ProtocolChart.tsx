"use client";

import { useMemo } from "react";
import { TrafficEvent } from "@/lib/types";

interface ProtocolStats {
  protocol: string;
  count: number;
  pct: number;
  color: string;
}

const PROTOCOL_COLORS: Record<string, string> = {
  dns: "#60a5fa",
  tls: "#34d399",
  mdns: "#f472b6",
  http: "#fbbf24",
  arp: "#a78bfa",
  icmp: "#fb923c",
  tcp: "#6ee7b7",
  udp: "#93c5fd",
  other: "#64748b",
};

interface ProtocolChartProps {
  events: TrafficEvent[];
  domains: Record<string, { kinds: Record<string, number> }>;
}

export default function ProtocolChart({ events, domains }: ProtocolChartProps) {
  const stats = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const e of events) {
      counts[e.kind] = (counts[e.kind] || 0) + 1;
    }
    // Also count from domains
    for (const d of Object.values(domains)) {
      for (const [k, n] of Object.entries(d.kinds || {})) {
        counts[k] = (counts[k] || 0) + n;
      }
    }
    const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
    return Object.entries(counts)
      .map(([protocol, count]) => ({
        protocol,
        count,
        pct: Math.round((count / total) * 100),
        color: PROTOCOL_COLORS[protocol] || PROTOCOL_COLORS.other,
      }))
      .sort((a, b) => b.count - a.count);
  }, [events, domains]);

  const maxCount = stats.length > 0 ? stats[0].count : 1;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Protocol Distribution
      </h3>
      <div className="space-y-2">
        {stats.map((s) => (
          <div key={s.protocol} className="flex items-center gap-2">
            <span className="w-12 text-[10px] font-medium uppercase text-slate-400">
              {s.protocol}
            </span>
            <div className="flex-1">
              <div className="h-4 overflow-hidden rounded bg-slate-800">
                <div
                  className="h-full rounded transition-all duration-500"
                  style={{
                    width: `${Math.max(2, (s.count / maxCount) * 100)}%`,
                    backgroundColor: s.color,
                  }}
                />
              </div>
            </div>
            <span className="w-12 text-right font-mono text-[10px] text-slate-500">
              {s.count}
            </span>
            <span className="w-8 text-right text-[10px] text-slate-600">
              {s.pct}%
            </span>
          </div>
        ))}
      </div>
      {stats.length === 0 && (
        <div className="text-center text-xs text-slate-500">No protocol data</div>
      )}
    </div>
  );
}
