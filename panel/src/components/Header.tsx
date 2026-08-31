"use client";

interface HeaderProps {
  iface: string;
  packets: number;
  domainCount: number;
  deviceCount: number;
  onlineCount: number;
  updated: number;
  connected: boolean;
}

function fmtAgo(t: number): string {
  if (!t) return "never";
  const d = Date.now() / 1000 - t;
  if (d < 5) return "now";
  if (d < 60) return `${d.toFixed(0)}s ago`;
  if (d < 3600) return `${(d / 60).toFixed(0)}m ago`;
  return `${(d / 3600).toFixed(1)}h ago`;
}

export default function Header({
  iface,
  packets,
  domainCount,
  deviceCount,
  onlineCount,
  updated,
  connected,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
        <h1 className="text-sm font-semibold tracking-wide text-slate-100">
          netwatch
        </h1>

        <div
          className={`h-2 w-2 rounded-full transition-colors ${
            connected
              ? "bg-emerald-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]"
              : "bg-red-500"
          }`}
        />

        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
          <Pill label="iface" value={iface} />
          <Pill label="packets" value={packets.toLocaleString()} />
          <Pill label="domains" value={domainCount.toLocaleString()} />
          <Pill
            label="devices"
            value={`${onlineCount}/${deviceCount}`}
            accent={onlineCount > 0}
          />
          <Pill label="updated" value={fmtAgo(updated)} />
        </div>
      </div>
    </header>
  );
}

function Pill({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-800 bg-slate-900 px-2 py-0.5">
      <span className="text-slate-500">{label}</span>
      <span className={`font-medium ${accent ? "text-emerald-400" : "text-slate-200"}`}>
        {value}
      </span>
    </span>
  );
}
