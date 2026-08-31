"use client";

import { useMemo } from "react";
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

function deviceIcon(dev: MergedDevice): string {
  const h = (dev.hostname || "").toLowerCase();
  const v = (dev.vendor || "").toLowerCase();
  if (dev.ip === "192.168.2.1") return "🌐";
  if (h.includes("iphone") || h.includes("ipad")) return "📱";
  if (h.includes("macbook") || h.includes("mac")) return "💻";
  if (h.includes("apple-tv") || h.includes("appletv")) return "📺";
  if (h.includes("homepod")) return "🔊";
  if (v.includes("samsung")) return "📱";
  if (v.includes("google")) return "📱";
  return "📡";
}

interface PerDeviceActivityProps {
  devices: MergedDevice[];
  domains: Record<string, { count: number; devs: Record<string, number>; last: number }>;
}

export default function PerDeviceActivity({ devices, domains }: PerDeviceActivityProps) {
  const activeDevices = useMemo(() => {
    return devices
      .filter(d => d.traffic_events > 0)
      .sort((a, b) => b.traffic_events - a.traffic_events);
  }, [devices]);

  if (activeDevices.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-500">
        Waiting for device activity...
     </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
      {activeDevices.map(dev => {
        const deviceDomains = Object.entries(domains)
          .filter(([, info]) => (info.devs || {})[dev.ip])
          .sort(([, a], [, b]) => b.count - a.count)
          .slice(0, 8);

        return (
          <div
            key={dev.ip}
            className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 hover:border-slate-600 transition-colors"
          >
            <div className="mb-2 flex items-center gap-2">
              <span className="text-lg">{deviceIcon(dev)}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-100 truncate">
                  {dev.hostname || dev.ip}
               </div>
                <div className="font-mono text-[10px] text-slate-500">{dev.ip}</div>
             </div>
              <span className="rounded bg-cyan-950 px-1.5 py-0.5 text-[10px] text-cyan-300">
                {dev.traffic_events}
             </span>
           </div>

            {deviceDomains.length > 0 ? (
              <div className="space-y-1">
                {deviceDomains.map(([domain, info]) => (
                  <div key={domain} className="flex items-center gap-2">
                    <span className="flex-1 truncate font-mono text-[11px] text-slate-300">
                      {formatDomain(domain)}
                   </span>
                    <span className="text-[10px] text-slate-500">{info.count}×</span>
                 </div>
                ))}
             </div>
            ) : (
              <div className="text-[10px] text-slate-500">No domains yet</div>
            )}
         </div>
        );
      })}
   </div>
  );
}
