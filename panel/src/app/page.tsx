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
import TopologyMap from "@/components/TopologyMap";
import TrafficTimeline from "@/components/TrafficTimeline";
import GeoMap from "@/components/GeoMap";
import SankeyFlow from "@/components/SankeyFlow";
import WorldMap from "@/components/WorldMap";
import { useLiveData } from "@/lib/useLiveData";
import { MergedDevice } from "@/lib/types";

const POLL_MS = parseInt(process.env.NEXT_PUBLIC_POLL_MS || "2000", 10);
type Tab = "live" | "wifi" | "devices";

function getDeviceType(dev: MergedDevice): { icon: string; label: string } {
  const h = (dev.hostname || "").toLowerCase();
  const v = (dev.vendor || "").toLowerCase();
  const p = dev.protocols || {};
  const hasMdns = (p.mdns || 0) > 0;
  const hasTls = (p.tls || 0) > 0;
  const domainList = Object.keys(dev.domains || {});
  const hasChromecast = domainList.some(d => d.includes("googlecast"));

  if (dev.ip === "192.168.2.1") return { icon: "🌐", label: "Router" };
  if (h.includes("iphone") || h.includes("ipad")) return { icon: "📱", label: "iOS Device" };
  if (h.includes("macbook") || h.includes("mac")) return { icon: "💻", label: "MacBook" };
  if (h.includes("apple-tv") || h.includes("appletv")) return { icon: "📺", label: "Apple TV" };
  if (h.includes("homepod")) return { icon: "🔊", label: "HomePod" };
  if (hasChromecast) return { icon: "📺", label: "Chromecast" };
  if (v.includes("samsung")) return { icon: "📱", label: "Samsung Device" };
  if (v.includes("sonos")) return { icon: "🔊", label: "Sonos" };
  if (v.includes("ring") || v.includes("nest")) return { icon: "📷", label: "Smart Camera" };
  if (v.includes("ubiquiti") || v.includes("cisco") || v.includes("netgear")) return { icon: "🌐", label: "Network Device" };
  if (hasTls && !hasMdns) return { icon: "💻", label: "Device (active)" };
  if (hasMdns) return { icon: "📡", label: "Smart Device" };
  return { icon: "📡", label: "Device" };
}

function formatDomain(domain: string): string {
  // Strip trailing dots, .local, etc.
  let d = domain.replace(/\.$/, "");
  if (d.endsWith(".local")) return d;
  // For reverse DNS, show cleaned up
  if (d.endsWith(".in-addr.arpa")) {
    const parts = d.replace(".in-addr.arpa", "").split(".").reverse();
    return parts.join(".");
  }
  // For mDNS sub-services, show the parent service
  if (d.startsWith("_") && d.includes("._")) {
    const match = d.match(/_([^._]+\.[^._]+)\.local/);
    if (match) return match[1] + ".local";
  }
  return d;
}

function mergeDevices(traffic: ReturnType<typeof useLiveData>["traffic"], discovered: ReturnType<typeof useLiveData>["devices"]): MergedDevice[] {
  const map = new Map<string, MergedDevice>();

  // Start with discovered devices (full info from devices.json)
  if (discovered?.devices) {
    for (const [ip, dev] of Object.entries(discovered.devices)) {
      map.set(ip, {
        ip: dev.ip || ip,
        mac: dev.mac || "",
        vendor: dev.vendor || "",
        hostname: dev.hostname || "",
        interface: dev.interface || "",
        first_seen: dev.first_seen || 0,
        last_seen: dev.last_seen || 0,
        online: dev.online ?? true,
        traffic_events: dev.traffic_events || 0,
        domains: dev.domains || {},
        protocols: dev.protocols || {},
        activity_level: "idle",
      });
    }
  }

  // Merge traffic data (from SSE/state.json)
  if (traffic?.devices) {
    for (const [ip, td] of Object.entries(traffic.devices)) {
      const existing = map.get(ip);
      if (existing) {
        existing.traffic_events = Math.max(existing.traffic_events, td.count || 0);
        existing.domains = td.domains || existing.domains;
        if (td.last) existing.last_seen = Math.max(existing.last_seen, td.last);
        if (td.first) existing.first_seen = Math.min(existing.first_seen || td.first, td.first);
        if ((td.count || 0) > 0) existing.online = true;
        if (td.protocols) existing.protocols = td.protocols;
      } else {
        map.set(ip, {
          ip, mac: "", vendor: "", hostname: "", interface: traffic.iface || "",
          first_seen: td.first || 0, last_seen: td.last || 0, online: true,
          traffic_events: td.count || 0, domains: td.domains || {},
          protocols: td.protocols || {},
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
  const { traffic, devices: discovered, connected } = useLiveData(POLL_MS);
  const [filter, setFilter] = useState("");
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("live");
  const [captures, setCaptures] = useState<{ name: string; size: number; mtime: number }[]>([]);
  const [selectedCapture, setSelectedCapture] = useState<string | null>(null);

  // Fetch captures separately
  useEffect(() => {
    const fetchCaptures = async () => {
      try {
        const res = await fetch("/api/captures", { cache: "no-store" });
        if (res.ok) {
          const d = await res.json();
          setCaptures(d.captures || []);
        }
      } catch {}
    };
    fetchCaptures();
    const id = setInterval(fetchCaptures, 5000);
    return () => clearInterval(id);
  }, []);

  const merged = mergeDevices(traffic, discovered);
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
        iface={traffic?.iface || discovered?.iface || "—"}
        packets={traffic?.packets || 0}
        domainCount={Object.keys(traffic?.domains || {}).length}
        deviceCount={merged.length}
        onlineCount={onlineCount}
        updated={traffic?.updated || discovered?.updated || 0}
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
            {/* Topology + Map */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <TopologyMap devices={merged} events={events} />
              <WorldMap domains={traffic?.domains || {}} />
            </div>
            {/* Timeline + Sankey */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <TrafficTimeline events={events} />
              <SankeyFlow events={events} devices={traffic?.devices || {}} />
            </div>
            {/* Stats row */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <ProtocolChart events={events} domains={traffic?.domains || {}} />
              <TopTalkers events={events} devices={traffic?.devices || {}} />
              <SecurityAlerts events={events} devices={traffic?.devices || {}} />
            </div>
            {/* Events + Domains */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <ActivityFeed events={events} filter={filter} />
              <TopDomains domains={traffic?.domains || {}} filter={filter} devices={merged} />
            </div>
          </div>
        )}

        {/* TAB: WiFi Analysis (tshark) */}
        {tab === "wifi" && (
          <div className="space-y-4">
            <CaptureManager
              captures={captures}
              onRefresh={() => {}}
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
              const level = dev.activity_level;
              const levelColor = level === "high" ? "text-emerald-400" : level === "medium" ? "text-amber-400" : level === "low" ? "text-slate-400" : "text-slate-600";
              const deviceType = getDeviceType(dev);
              const domains = Object.entries(dev.domains || {}).sort(([,a],[,b]) => b - a);
              return (
                <section className="rounded-lg border border-cyan-800/30 bg-cyan-950/10 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{deviceType.icon}</span>
                      <div>
                        <h3 className="text-sm font-semibold text-cyan-400">
                          {dev.hostname || dev.ip}
                        </h3>
                        <div className="flex items-center gap-2 text-[10px] text-slate-500">
                          <span>{deviceType.label}</span>
                          {dev.vendor && <span>·</span>}
                          {dev.vendor && <span className="text-cyan-400/60">{dev.vendor}</span>}
                        </div>
                      </div>
                      <span className={`text-xs font-medium ${levelColor}`}>{level.toUpperCase()}</span>
                    </div>
                    <button onClick={() => setSelectedDevice(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
                  </div>
                  <div className="mb-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-5">
                    <Detail label="IP Address" value={dev.ip} />
                    <Detail label="MAC Address" value={dev.mac || "—"} />
                    <Detail label="Hostname" value={dev.hostname || "—"} />
                    <Detail label="Vendor" value={dev.vendor || "—"} />
                    <Detail label="Interface" value={dev.interface || "—"} />
                    <Detail label="Traffic Events" value={dev.traffic_events.toLocaleString()} />
                    <Detail label="Unique Domains" value={domains.length.toLocaleString()} />
                    <Detail label="First Seen" value={dev.first_seen ? new Date(dev.first_seen * 1000).toLocaleString() : "—"} />
                    <Detail label="Last Seen" value={dev.last_seen ? new Date(dev.last_seen * 1000).toLocaleString() : "—"} />
                    <Detail label="Status" value={dev.online ? "Online" : "Offline"} />
                  </div>
                  {Object.keys(dev.protocols || {}).length > 0 && (
                    <div className="mb-3">
                      <div className="mb-1 text-[10px] text-slate-500">Protocols:</div>
                      <div className="flex gap-2">
                        {Object.entries(dev.protocols).sort(([,a],[,b]) => b-a).map(([k, n]) => (
                          <span key={k} className={`rounded px-2 py-0.5 text-[10px] font-medium uppercase ${
                            k === "dns" ? "bg-blue-950 text-blue-300" :
                            k === "tls" ? "bg-emerald-950 text-emerald-300" :
                            k === "mdns" ? "bg-pink-950 text-pink-300" :
                            "bg-slate-800 text-slate-400"
                          }`}>
                            {k}: {n}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {domains.length > 0 && (
                    <div>
                      <div className="mb-1 text-[10px] text-slate-500">Browsing History ({domains.length} domains):</div>
                      <div className="max-h-[200px] overflow-y-auto space-y-1">
                        {domains.map(([domain, count]) => (
                          <div key={domain} className="flex items-center justify-between rounded bg-slate-800/50 px-2 py-1">
                            <span className="font-mono text-[11px] text-slate-300 truncate">{formatDomain(domain)}</span>
                            <span className="text-[10px] text-slate-500 shrink-0 ml-2">{count}×</span>
                          </div>
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
