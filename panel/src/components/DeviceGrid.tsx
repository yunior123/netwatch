"use client";

import { MergedDevice } from "@/lib/types";

function fmtAgo(t: number): string {
  if (!t) return "never";
  const d = Date.now() / 1000 - t;
  if (d < 5) return "now";
  if (d < 60) return `${d.toFixed(0)}s`;
  if (d < 3600) return `${(d / 60).toFixed(0)}m`;
  return `${(d / 3600).toFixed(1)}h`;
}

function deviceActivity(dev: MergedDevice): "high" | "medium" | "low" | "idle" {
  if (dev.traffic_events === 0 && Object.keys(dev.domains).length === 0) return "idle";
  const ago = Date.now() / 1000 - dev.last_seen;
  if (ago < 120 && dev.traffic_events > 20) return "high";
  if (ago < 600 && dev.traffic_events > 5) return "medium";
  if (dev.traffic_events > 0) return "low";
  return "idle";
}

function activityColor(level: string): string {
  switch (level) {
    case "high": return "bg-emerald-400 shadow-[0_0_6px_rgba(74,222,128,0.4)]";
    case "medium": return "bg-amber-400";
    case "low": return "bg-slate-500";
    default: return "bg-slate-700";
  }
}

function activityLabel(level: string): string {
  switch (level) {
    case "high": return "High";
    case "medium": return "Medium";
    case "low": return "Low";
    default: return "Idle";
  }
}

function deviceIcon(dev: MergedDevice): string {
  // Use stored device_icon from Python detection (most accurate)
  if (dev.device_icon && dev.device_icon !== "📡") return dev.device_icon;
  // Fallback to hostname/vendor matching
  const h = (dev.hostname || "").toLowerCase();
  const v = (dev.vendor || "").toLowerCase();
  if (h.includes("iphone") || h.includes("ipad") || h.includes("phone")) return "📱";
  if (h.includes("macbook") || h.includes("mac")) return "💻";
  if (h.includes("apple-tv") || h.includes("appletv") || h.includes("rokutv") || h.includes("firestick")) return "📺";
  if (h.includes("homepod")) return "🔊";
  if (h.includes("watch")) return "⌚";
  if (h.includes("thermostat")) return "🌡️";
  if (h.includes("camera") || h.includes("c120")) return "📷";
  if (h.includes("tv")) return "📺";
  if (h.includes("pixel") || h.includes("galaxy") || h.includes("iphone") || h.includes("s24") || h.includes("s25")) return "📱";
  if (v.includes("samsung")) return "📱";
  if (v.includes("apple")) return "🍎";
  if (v.includes("google")) return "📱";
  if (v.includes("sonos")) return "🔊";
  if (v.includes("roku") || v.includes("xbox") || v.includes("playstation")) return "📺";
  if (v.includes("ring") || v.includes("nest")) return "📷";
  if (v.includes("ubiquiti") || v.includes("cisco") || v.includes("netgear") || v.includes("tp-link")) return "🌐";
  if (v.includes("printer") || v.includes("brother") || v.includes("canon") || v.includes("epson")) return "🖨️";
  if (v.includes("raspberry")) return "🥧";
  if (v.includes("docker") || v.includes("virtual")) return "🐳";
  if (dev.ip === "192.168.2.1" || h.includes("router") || h.includes("gateway") || h.includes("mynetwork")) return "🌐";
  return "📡";
}

function deviceName(dev: MergedDevice): string {
  // Use device_model if available (e.g. "Samsung Galaxy A04", "Amazon Fire TV")
  if (dev.device_model && dev.device_model !== "Unknown Device") return dev.device_model;
  // Use hostname if it's meaningful (not a MAC or random string)
  if (dev.hostname && !dev.hostname.match(/^[\d:a-f]{17}$/i) && dev.hostname !== "?") return dev.hostname;
  return dev.vendor || "Unknown";
}

interface DeviceGridProps {
  devices: MergedDevice[];
  onSelectDevice: (ip: string) => void;
  selectedDevice: string | null;
}

export default function DeviceGrid({ devices, onSelectDevice, selectedDevice }: DeviceGridProps) {
  if (devices.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-500">
        No devices discovered yet
      </div>
    );
  }

  const sorted = [...devices].sort((a, b) => {
    const al = deviceActivity(a);
    const bl = deviceActivity(b);
    const order = { high: 0, medium: 1, low: 2, idle: 3 };
    if (order[al] !== order[bl]) return order[al] - order[bl];
    return b.traffic_events - a.traffic_events;
  });

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {sorted.map((dev) => {
        const level = deviceActivity(dev);
        const isSelected = selectedDevice === dev.ip;
        return (
          <button
            key={dev.ip}
            onClick={() => onSelectDevice(dev.ip)}
            className={`group rounded-lg border p-3 text-left transition-all hover:border-slate-600 hover:bg-slate-800/50 ${
              isSelected
                ? "border-cyan-600 bg-slate-800/80 ring-1 ring-cyan-600/30"
                : "border-slate-800 bg-slate-900/50"
            }`}
          >
            <div className="mb-2 flex items-start justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">{deviceIcon(dev)}</span>
                <div>
                  <div className="text-sm font-medium text-slate-100">
                    {deviceName(dev)}
                  </div>
                  <div className="font-mono text-xs text-slate-500">{dev.ip}</div>
                  {dev.vendor && dev.vendor !== deviceName(dev) && (
                    <div className="text-[10px] text-cyan-400/60">{dev.vendor}</div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <div className={`h-1.5 w-1.5 rounded-full ${activityColor(level)}`} />
                <span className="text-[10px] text-slate-500">{activityLabel(level)}</span>
              </div>
            </div>

            <div className="mb-2 flex gap-1.5 font-mono text-[10px] text-slate-600">
              <span className="truncate">{dev.mac}</span>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>
                {dev.traffic_events} event{dev.traffic_events !== 1 ? "s" : ""}
              </span>
              <span>{Object.keys(dev.domains).length} host{Object.keys(dev.domains).length !== 1 ? "s" : ""}</span>
              <span className="text-slate-600">{fmtAgo(dev.last_seen)}</span>
            </div>

            {Object.keys(dev.domains).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {Object.entries(dev.domains)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 3)
                  .map(([domain, count]) => (
                    <span
                      key={domain}
                      className="inline-block rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400"
                    >
                      {domain}
                    </span>
                  ))}
                {Object.keys(dev.domains).length > 3 && (
                  <span className="text-[10px] text-slate-600">
                    +{Object.keys(dev.domains).length - 3}
                  </span>
                )}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
