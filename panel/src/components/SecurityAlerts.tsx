"use client";

import { useMemo } from "react";

interface Alert {
  id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  type: string;
  message: string;
  source: string;
  timestamp: number;
}

function severityColor(s: string): string {
  switch (s) {
    case "critical": return "bg-red-500/20 text-red-400 border-red-500/30";
    case "high": return "bg-orange-500/20 text-orange-400 border-orange-500/30";
    case "medium": return "bg-amber-500/20 text-amber-400 border-amber-500/30";
    case "low": return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    default: return "bg-slate-500/20 text-slate-400 border-slate-500/30";
  }
}

function severityIcon(s: string): string {
  switch (s) {
    case "critical": return "🔴";
    case "high": return "🟠";
    case "medium": return "🟡";
    case "low": return "🔵";
    default: return "⚪";
  }
}

interface SecurityAlertsProps {
  events: Array<{ t: number; dev: string; kind: string; host: string }>;
  devices: Record<string, { count: number; protocols?: Record<string, number> }>;
}

export default function SecurityAlerts({ events, devices }: SecurityAlertsProps) {
  const alerts = useMemo(() => {
    const result: Alert[] = [];

    // Check for high event volume from single device (possible scan)
    const devCounts = new Map<string, number>();
    const devHosts = new Map<string, Set<string>>();
    for (const e of events) {
      devCounts.set(e.dev, (devCounts.get(e.dev) || 0) + 1);
      if (!devHosts.has(e.dev)) devHosts.set(e.dev, new Set());
      devHosts.get(e.dev)!.add(e.host);
    }

    for (const [dev, count] of devCounts) {
      if (count > 50) {
        result.push({
          id: `scan-${dev}`,
          severity: "high",
          type: "Possible Scan",
          message: `${dev} generated ${count} events — possible port/DNS scan`,
          source: dev,
          timestamp: Date.now() / 1000,
        });
      }
      const hosts = devHosts.get(dev);
      if (hosts && hosts.size > 20) {
        result.push({
          id: `recon-${dev}`,
          severity: "medium",
          type: "Recon Activity",
          message: `${dev} contacted ${hosts.size} unique hosts — possible reconnaissance`,
          source: dev,
          timestamp: Date.now() / 1000,
        });
      }
    }

    // Check for suspicious domains
    const suspiciousPatterns = [
      /\.tk$/i, /\.ml$/i, /\.ga$/i, /\.cf$/i, /\.gq$/i, // free TLDs
      /phish/i, /malware/i, /exploit/i, /hack/i,
      /tor2web/i, /onion/i,
    ];
    const domainCounts = new Map<string, number>();
    for (const e of events) {
      domainCounts.set(e.host, (domainCounts.get(e.host) || 0) + 1);
    }
    for (const [domain, count] of domainCounts) {
      for (const pat of suspiciousPatterns) {
        if (pat.test(domain)) {
          result.push({
            id: `suspicious-${domain}`,
            severity: "medium",
            type: "Suspicious Domain",
            message: `Contact with suspicious domain: ${domain} (${count}x)`,
            source: domain,
            timestamp: Date.now() / 1000,
          });
          break;
        }
      }
    }

    // Check for deauth flood (from tshark WiFi analysis — placeholder)
    // Check for devices with no hostname (potential rogue)
    for (const [ip, dev] of Object.entries(devices)) {
      if (dev.count > 0 && !ip.includes("192.168.") && !ip.includes("10.") && !ip.includes("172.")) {
        // External IP generating traffic — unusual
        result.push({
          id: `external-${ip}`,
          severity: "info",
          type: "External Traffic",
          message: `External IP ${ip} generated ${dev.count} events`,
          source: ip,
          timestamp: Date.now() / 1000,
        });
      }
    }

    return result
      .sort((a, b) => {
        const order = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
        return (order[a.severity] ?? 5) - (order[b.severity] ?? 5);
      })
      .slice(0, 20);
  }, [events, devices]);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Security Alerts
        </h3>
        {alerts.length > 0 && (
          <span className="rounded bg-red-900/30 px-1.5 py-0.5 text-[10px] text-red-400">
            {alerts.length}
          </span>
        )}
      </div>
      <div className="max-h-[300px] space-y-1.5 overflow-y-auto">
        {alerts.map((a) => (
          <div
            key={a.id}
            className={`rounded border px-2.5 py-1.5 text-xs ${severityColor(a.severity)}`}
          >
            <div className="flex items-start gap-1.5">
              <span className="mt-0.5">{severityIcon(a.severity)}</span>
              <div className="flex-1">
                <div className="font-medium">{a.type}</div>
                <div className="text-[10px] opacity-75">{a.message}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
      {alerts.length === 0 && (
        <div className="py-2 text-center text-xs text-emerald-400/60">
          No security alerts — all clear
        </div>
      )}
    </div>
  );
}
