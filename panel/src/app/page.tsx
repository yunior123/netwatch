"use client";

import { useEffect, useState, useCallback } from "react";
import Header from "@/components/Header";
import DeviceGrid from "@/components/DeviceGrid";
import ActivityFeed from "@/components/ActivityFeed";
import TopDomains from "@/components/TopDomains";
import WifiAnalysis from "@/components/WifiAnalysis";
import CaptureManager from "@/components/CaptureManager";
import ProtocolChart from "@/components/ProtocolChart";
import TopTalkers from "@/components/TopTalkers";
import SecurityAlerts from "@/components/SecurityAlerts";
import { TrafficState, DevicesState, MergedDevice } from "@/lib/types";

const POLL_MS = parseInt(process.env.NEXT_PUBLIC_POLL_MS || "2000", 10);
type Tab = "live" | "wifi" | "devices";

function mergeDevices(traffic: TrafficState | null, discovered: DevicesState | null): MergedDevice[] {
  const map = new Map<string, MergedDevice>();

  if (discovered?.devices) {
    for (const [ip, dev] of Object.entries(discovered.devices)) {
      map.set(ip, { ...dev, activity_level: "idle" });
    }
  }

  if (traffic?.devices) {
    for (const [ip, td] of Object.entries(traffic.devices)) {
      const existing = map.get(ip);
      if (existing) {
        existing.traffic_events = td.count;
        existing.domains = td.domains || {};
        existing.last_seen = Math.max(existing.last_seen, td.last);
        existing.first_seen = Math.min(existing.first_seen, td.first);
        if (td.count > 0) existing.online = true;
      } else {
        map.set(ip, {
          ip, mac: "", hostname: "", interface: traffic.iface || "",
          first_seen: td.first, last_seen: td.last, online: true,
          traffic_events: td.count, domains: td.domains || {}, protocols: {},
          activity_level: "idle",
        });
      }
    }
  }

  const now = Date.now() / 1000;
  for (const dev of map.values()) {
    const ago = now - dev.last_seen;
    if (dev.traffic_events === 0 && Object.keys(dev.domains).length === 0) dev.activity_level = "idle";
    else if (ago < 120 && dev.traffic_events > 20) dev.activity_level = "high";
    else if (ago < 600 && dev.traffic_events > 5) dev.activity_level = "medium";
    else if (dev.traffic_events > 0) dev.activity_level = "low";
    else dev.activity_level = "idle";
  }

  return Array.from(map.values());
}

export default function Home() {
  const [traffic, setTraffic] = useState<TrafficState | null>(null);
  const [devices, setDevices] = useState<DevicesState | null>(null);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState("");
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("live");
  const [captures, setCaptures] = useState<{ name: string; size: number; mtime: number }[]>([]);
  const [selectedCapture, setSelectedCapture] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [tRes, dRes, cRes] = await Promise.all([
        fetch("/api/state", { cache: "no-store" }),
        fetch("/api/devices", { cache: "no-store" }),
        fetch("/api/captures", { cache: "no-store" }),
      ]);
      if (tRes.ok) setTraffic(await tRes.json());
      if (dRes.ok) setDevices(await dRes.json());
      if (cRes.ok) {
        const d = await cRes.json();
        setCaptures(d.captures || []);
      }
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, POLL_MS);
    return () => clearInterval(id);
  }, [fetchData]);

  const merged = mergeDevices(traffic, devices);
  const onlineCount = merged.filter((d) => d.online).length;
  const events = traffic?.events || [];

  const TABS: { key: Tab; label: string; icon: string }[] = [
    { key: "live", label: "Live Traffic", icon: "📡" },
    { key: "wifi", label: "WiFi Analysis", icon: "🔬" },
    { key: "devices", label: "All Devices", icon: "📱" },
  ];

  return (
    <div className="min-h-screen bg-[#0a0c10] text-slate-200">
      <Header
        iface={traffic?.iface || devices?.iface || "—"}
        packets={traffic?.packets || 0}
        domainCount={Object.keys(traffic?.domains || {}).length}
        deviceCount={merged.length}
        onlineCount={onlineCount}
        updated={traffic?.updated || devices?.updated || 0}
        connected={connected}
      />

      <main className="mx-auto max-w-[1600px] space-y-4 p-4">
        {/* Tabs */}
        <div className="flex gap-1 rounded-lg border border-slate-800 bg-slate-900/50 p-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                tab === t.key
                  ? "bg-cyan-700 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {t.icon} {t.label}
              {t.key === "devices" && <span className="ml-1 text-xs opacity-60">({merged.length})</span>}
              {t.key === "live" && <span className="ml-1 text-xs opacity-60">({events.length})</span>}
            </button>
          ))}
        </div>

        {/* Search (always visible) */}
        <div className="relative">
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter by host, device, IP, or kind..."
            className="w-full rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-2.5 text-sm text-slate-200 placeholder-slate-600 outline-none transition-colors focus:border-cyan-700 focus:ring-1 focus:ring-cyan-700/30"
          />
          {filter && (
            <button onClick={() => setFilter("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400">
              Clear
            </button>
          )}
        </div>

        {/* TAB: Live Traffic */}
        {tab === "live" && (
          <div className="space-y-4">
            {/* Stats row */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <ProtocolChart events={events} domains={traffic?.domains || {}} />
              <TopTalkers events={events} devices={traffic?.devices || {}} />
              <SecurityAlerts events={events} devices={traffic?.devices || {}} />
            </div>
            {/* Events + Domains */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <ActivityFeed events={events} filter={filter} />
              <TopDomains domains={traffic?.domains || {}} filter={filter} />
            </div>
          </div>
        )}

        {/* TAB: WiFi Analysis (tshark) */}
        {tab === "wifi" && (
          <div className="space-y-4">
            <CaptureManager
              captures={captures}
              onRefresh={fetchData}
              onSelect={(name) => setSelectedCapture(selectedCapture === name ? null : name)}
              selected={selectedCapture}
            />
            <WifiAnalysis
              captures={captures}
              selectedCapture={selectedCapture}
              onSelectCapture={setSelectedCapture}
            />
          </div>
        )}

        {/* TAB: All Devices */}
        {tab === "devices" && (
          <div className="space-y-4">
            <section>
              <DeviceGrid
                devices={merged.filter((d) => {
                  if (!filter) return true;
                  const q = filter.toLowerCase();
                  return d.ip.includes(q) || d.mac.toLowerCase().includes(q) || d.hostname.toLowerCase().includes(q);
                })}
                onSelectDevice={(ip) => setSelectedDevice(selectedDevice === ip ? null : ip)}
                selectedDevice={selectedDevice}
              />
            </section>

            {selectedDevice && (() => {
              const dev = merged.find((d) => d.ip === selectedDevice);
              if (!dev) return null;
              return (
                <section className="rounded-lg border border-cyan-800/30 bg-cyan-950/10 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
                      Device Detail: {dev.hostname || dev.ip}
                    </h3>
                    <button onClick={() => setSelectedDevice(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
                  </div>
                  <div className="mb-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                    <Detail label="IP" value={dev.ip} />
                    <Detail label="MAC" value={dev.mac || "—"} />
                    <Detail label="Hostname" value={dev.hostname || "—"} />
                    <Detail label="Interface" value={dev.interface || "—"} />
                    <Detail label="Traffic Events" value={dev.traffic_events.toLocaleString()} />
                    <Detail label="Domains" value={Object.keys(dev.domains).length.toLocaleString()} />
                    <Detail label="First Seen" value={new Date(dev.first_seen * 1000).toLocaleString()} />
                    <Detail label="Last Seen" value={new Date(dev.last_seen * 1000).toLocaleString()} />
                  </div>
                  {Object.keys(dev.protocols || {}).length > 0 && (
                    <div className="mb-3 flex gap-2">
                      {Object.entries(dev.protocols).map(([k, n]) => (
                        <span key={k} className={`rounded px-2 py-0.5 text-[10px] font-medium uppercase ${
                          k === "dns" ? "bg-blue-950 text-blue-300" :
                          k === "tls" ? "bg-emerald-950 text-emerald-300" :
                          "bg-pink-950 text-pink-300"
                        }`}>
                          {k}: {n}
                        </span>
                      ))}
                    </div>
                  )}
                  {Object.keys(dev.domains).length > 0 && (
                    <div>
                      <div className="mb-1 text-[10px] text-slate-500">Domains contacted:</div>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(dev.domains).sort(([, a], [, b]) => b - a).map(([domain, count]) => (
                          <span key={domain} className="inline-block rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                            {domain} ({count})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </section>
              );
            })()}
          </div>
        )}
      </main>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-slate-500">{label}</div>
      <div className="font-mono text-slate-300">{value}</div>
    </div>
  );
}
