"use client";

import { useRef, useEffect, useMemo, useCallback } from "react";
import { MergedDevice } from "@/lib/types";

interface Node {
  id: string;
  ip: string;
  label: string;
  sublabel: string;
  type: "router" | "phone" | "laptop" | "iot" | "server" | "unknown";
  angle: number;
  dist: number;
  radius: number;
  color: string;
  online: boolean;
}

function deviceType(dev: MergedDevice): Node["type"] {
  const h = dev.hostname.toLowerCase();
  const v = (dev.vendor || "").toLowerCase();
  if (dev.ip === "192.168.2.1" || h.includes("router")) return "router";
  if (h.includes("iphone") || h.includes("ipad") || h.includes("phone") || v.includes("samsung") || v.includes("google")) return "phone";
  if (h.includes("macbook") || h.includes("mac") || v.includes("apple") || v.includes("dell") || v.includes("lenovo")) return "laptop";
  if (v.includes("sonos") || v.includes("roku") || v.includes("ring") || v.includes("nest") || v.includes("tv")) return "iot";
  if (v.includes("raspberry") || v.includes("docker")) return "server";
  return "unknown";
}

function typeColor(type: Node["type"], online: boolean): string {
  if (!online) return "#334155";
  switch (type) {
    case "router": return "#f59e0b";
    case "phone": return "#3b82f6";
    case "laptop": return "#10b981";
    case "iot": return "#a855f7";
    case "server": return "#ef4444";
    default: return "#64748b";
  }
}

function typeIcon(type: Node["type"]): string {
  switch (type) {
    case "router": return "🌐";
    case "phone": return "📱";
    case "laptop": return "💻";
    case "iot": return "📡";
    case "server": return "🖥️";
    default: return "❓";
  }
}

interface TopologyMapProps {
  devices: MergedDevice[];
  events: Array<{ dev: string; host: string }>;
}

export default function TopologyMap({ devices, events }: TopologyMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hoverRef = useRef<string | null>(null);
  const animRef = useRef<number>(0);

  const graphData = useMemo(() => {
    const trafficMap = new Map<string, number>();
    for (const e of events) {
      trafficMap.set(e.dev, (trafficMap.get(e.dev) || 0) + 1);
    }

    const nodes: Node[] = [];
    // Router at center
    nodes.push({
      id: "router", ip: "192.168.2.1", label: "Router", sublabel: "Gateway",
      type: "router", angle: 0, dist: 0, radius: 26,
      color: typeColor("router", true), online: true,
    });

    const devs = devices.filter(d => d.ip !== "192.168.2.1");
    const angleStep = (2 * Math.PI) / Math.max(devs.length, 1);

    for (let i = 0; i < devs.length; i++) {
      const dev = devs[i];
      const type = deviceType(dev);
      const traffic = trafficMap.get(dev.ip) || 0;
      nodes.push({
        id: dev.ip, ip: dev.ip,
        label: dev.hostname || dev.ip,
        sublabel: dev.vendor || "",
        type,
        angle: angleStep * i - Math.PI / 2,
        dist: 160,
        radius: Math.min(24, 12 + traffic * 0.4),
        color: typeColor(type, dev.online),
        online: dev.online,
      });
    }

    return nodes;
  }, [devices, events]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const cx = w / 2;
    const cy = h / 2;

    // Clear
    ctx.fillStyle = "rgba(15, 23, 42, 0.95)";
    ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = "rgba(51, 65, 85, 0.1)";
    ctx.lineWidth = 0.5;
    for (let x = 0; x < w; x += 50) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 50) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

    const nodes = graphData;
    const hover = hoverRef.current;

    // Draw edges
    const router = nodes.find(n => n.id === "router")!;
    for (const node of nodes) {
      if (node.id === "router") continue;
      const nx = cx + Math.cos(node.angle) * node.dist;
      const ny = cy + Math.sin(node.angle) * node.dist;
      const isHover = hover === node.id;

      ctx.strokeStyle = isHover ? "rgba(59, 130, 246, 0.5)" : "rgba(71, 85, 105, 0.2)";
      ctx.lineWidth = isHover ? 2 : 1;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(nx, ny);
      ctx.stroke();

      // Particle
      if (node.online) {
        const t = (Date.now() % 5000) / 5000;
        const px = cx + (nx - cx) * t;
        const py = cy + (ny - cy) * t;
        ctx.fillStyle = isHover ? "rgba(59, 130, 246, 0.8)" : "rgba(100, 116, 139, 0.4)";
        ctx.beginPath();
        ctx.arc(px, py, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Draw nodes
    for (const node of nodes) {
      const nx = cx + Math.cos(node.angle) * node.dist;
      const ny = cy + Math.sin(node.angle) * node.dist;
      const isHover = hover === node.id;
      const r = node.radius * (isHover ? 1.15 : 1);

      // Glow
      if (node.online && node.type !== "unknown") {
        const g = ctx.createRadialGradient(nx, ny, r * 0.3, nx, ny, r * 2);
        g.addColorStop(0, node.color + "30");
        g.addColorStop(1, "transparent");
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(nx, ny, r * 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Circle
      ctx.fillStyle = node.color;
      ctx.beginPath();
      ctx.arc(nx, ny, r, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = isHover ? "#fff" : "rgba(255,255,255,0.15)";
      ctx.lineWidth = isHover ? 2 : 1;
      ctx.stroke();

      // Icon
      ctx.font = `${r * 0.6}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(typeIcon(node.type), nx, ny);

      // Label
      ctx.font = "bold 9px monospace";
      ctx.fillStyle = isHover ? "#fff" : "rgba(203, 213, 225, 0.8)";
      ctx.fillText(node.label, nx, ny + r + 11);

      // Sublabel on hover
      if (isHover && node.sublabel) {
        ctx.font = "8px sans-serif";
        ctx.fillStyle = "rgba(148, 163, 184, 0.6)";
        ctx.fillText(node.sublabel, nx, ny + r + 22);
      }
    }

    animRef.current = requestAnimationFrame(draw);
  }, [graphData]);

  useEffect(() => {
    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [draw]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;

    let found: string | null = null;
    for (const node of graphData) {
      const nx = cx + Math.cos(node.angle) * node.dist;
      const ny = cy + Math.sin(node.angle) * node.dist;
      const dx = mx - nx;
      const dy = my - ny;
      if (dx * dx + dy * dy < node.radius * node.radius * 2) {
        found = node.id;
        break;
      }
    }
    hoverRef.current = found;
    canvas.style.cursor = found ? "pointer" : "default";
  }, [graphData]);

  return (
    <div className="relative rounded-lg border border-slate-800 bg-slate-900/50 overflow-hidden">
      <div className="absolute left-3 top-3 z-10 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Network Topology
      </div>
      <div className="absolute right-3 top-3 z-10 flex gap-2 text-[10px] text-slate-500">
        <span>🌐 Router</span>
        <span>📱 Phone</span>
        <span>💻 Laptop</span>
        <span>📡 IoT</span>
        <span>🖥️ Server</span>
      </div>
      <canvas ref={canvasRef} className="h-[350px] w-full" onMouseMove={handleMouseMove} />
    </div>
  );
}
