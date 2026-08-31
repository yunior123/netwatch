"use client";

import { useMemo } from "react";
import { TrafficEvent } from "@/lib/types";

interface Talker {
  ip: string;
  events: number;
  hosts: Set<string>;
  lastSeen: number;
}

interface TopTalkersProps {
  events: TrafficEvent[];
  devices: Record<string, { count: number; n_domains: number }>;
}

export default function TopTalkers({ events, devices }: TopTalkersProps) {
  const talkers = useMemo(() => {
    const map = new Map<string, Talker>();
    for (const e of events) {
      let t = map.get(e.dev);
      if (!t) {
        t = { ip: e.dev, events: 0, hosts: new Set(), lastSeen: 0 };
        map.set(e.dev, t);
      }
      t.events++;
      t.hosts.add(e.host);
      if (e.t > t.lastSeen) t.lastSeen = e.t;
    }
    // Merge device data
    for (const [ip, dev] of Object.entries(devices)) {
      let t = map.get(ip);
      if (t) {
        t.events = Math.max(t.events, dev.count);
      } else {
        map.set(ip, { ip, events: dev.count, hosts: new Set(), lastSeen: 0 });
      }
    }
    return Array.from(map.values())
      .sort((a, b) => b.events - a.events)
      .slice(0, 15);
  }, [events, devices]);

  const maxEvents = talkers.length > 0 ? talkers[0].events : 1;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Top Talkers
      </h3>
      <div className="space-y-1.5">
        {talkers.map((t) => (
          <div key={t.ip} className="flex items-center gap-2 rounded px-2 py-1 hover:bg-slate-800/50">
            <span className="w-[120px] truncate font-mono text-xs text-amber-300" title={t.ip}>
              {t.ip}
            </span>
            <div className="flex-1">
              <div className="h-3 overflow-hidden rounded bg-slate-800">
                <div
                  className="h-full rounded bg-gradient-to-r from-amber-600 to-amber-400 transition-all duration-500"
                  style={{ width: `${(t.events / maxEvents) * 100}%` }}
                />
              </div>
            </div>
            <span className="w-10 text-right font-mono text-[10px] text-slate-500">
              {t.events}
            </span>
            <span className="w-8 text-center text-[10px] text-slate-600">
              {t.hosts.size || "—"}
            </span>
          </div>
        ))}
      </div>
      {talkers.length === 0 && (
        <div className="text-center text-xs text-slate-500">No traffic data</div>
      )}
    </div>
  );
}
