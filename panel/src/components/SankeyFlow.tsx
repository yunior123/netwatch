"use client";

import { useMemo, useRef, useEffect, useCallback } from "react";

interface FlowEntry {
  srcIp: string;
  srcName: string;
  dstHost: string;
  kind: string;
  count: number;
}

interface SankeyFlowProps {
  events: Array<{ dev: string; host: string; kind: string }>;
  devices: Record<string, { count: number; domains?: Record<string, number>; n_domains?: number }>;
}

export default function SankeyFlow({ events, devices }: SankeyFlowProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const flows = useMemo(() => {
    const map = new Map<string, FlowEntry>();
    for (const e of events) {
      const key = `${e.dev}|${e.host}|${e.kind}`;
      const existing = map.get(key);
      if (existing) {
        existing.count++;
      } else {
        map.set(key, {
          srcIp: e.dev,
          srcName: devices[e.dev]?.domains ? e.dev : e.dev,
          dstHost: e.host,
          kind: e.kind,
          count: 1,
        });
      }
    }
    return Array.from(map.values())
      .sort((a, b) => b.count - a.count)
      .slice(0, 20);
  }, [events, devices]);

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
    const pad = { top: 35, right: 20, bottom: 20, left: 20 };
    const nodeW = 14;
    const gap = 6;

    // Clear
    ctx.fillStyle = "rgba(15, 23, 42, 0.95)";
    ctx.fillRect(0, 0, w, h);

    if (flows.length === 0) {
      ctx.fillStyle = "#64748b";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Waiting for traffic data...", w / 2, h / 2);
      return;
    }

    // Build node lists
    const srcNodes = new Map<string, { label: string; total: number; y: number; h: number }>();
    const dstNodes = new Map<string, { label: string; total: number; y: number; h: number }>();

    // Aggregate by source and destination
    for (const f of flows) {
      const src = srcNodes.get(f.srcIp) || { label: f.srcIp, total: 0, y: 0, h: 0 };
      src.total += f.count;
      srcNodes.set(f.srcIp, src);

      const dst = dstNodes.get(f.dstHost) || { label: f.dstHost, total: 0, y: 0, h: 0 };
      dst.total += f.count;
      dstNodes.set(f.dstHost, dst);
    }

    // Layout left nodes (sources)
    const leftX = pad.left + 100;
    const rightX = w - pad.right - 100;
    const totalLeftH = Array.from(srcNodes.values()).reduce((a, n) => a + n.total, 0) * 1;
    const leftAvailable = h - pad.top - pad.bottom;
    const leftScale = Math.min(1, leftAvailable / Math.max(totalLeftH, 1));

    let ly = pad.top;
    for (const node of srcNodes.values()) {
      node.h = node.total * leftScale;
      node.y = ly;
      ly += node.h + gap;
    }

    // Layout right nodes (destinations)
    const totalRightH = Array.from(dstNodes.values()).reduce((a, n) => a + n.total, 0) * 1;
    const rightScale = Math.min(1, leftAvailable / Math.max(totalRightH, 1));

    let ry = pad.top;
    for (const node of dstNodes.values()) {
      node.h = node.total * rightScale;
      node.y = ry;
      ry += node.h + gap;
    }

    // Track y offsets for flow positioning
    const srcOffsets = new Map<string, number>();
    const dstOffsets = new Map<string, number>();
    for (const [k, v] of srcNodes) srcOffsets.set(k, v.y);
    for (const [k, v] of dstNodes) dstOffsets.set(k, v.y);

    // Kind colors
    const kindColor: Record<string, string> = {
      dns: "#3b82f6",
      tls: "#10b981",
      mdns: "#f472b6",
      other: "#64748b",
    };

    // Draw flows (curved bezier from left to right)
    for (const f of flows) {
      const src = srcNodes.get(f.srcIp);
      const dst = dstNodes.get(f.dstHost);
      if (!src || !dst) continue;

      const srcOff = srcOffsets.get(f.srcIp)!;
      const dstOff = dstOffsets.get(f.dstHost)!;
      const flowH = Math.max(2, f.count * leftScale);

      const x0 = leftX + nodeW;
      const y0 = srcOff + flowH / 2;
      const x1 = rightX;
      const y1 = dstOff + flowH / 2;

      srcOffsets.set(f.srcIp, srcOff + flowH);
      dstOffsets.set(f.dstHost, dstOff + flowH);

      const color = kindColor[f.kind] || kindColor.other;

      // Draw bezier flow
      ctx.beginPath();
      ctx.moveTo(x0, y0 - flowH / 2);
      ctx.bezierCurveTo(x0 + (x1 - x0) * 0.4, y0 - flowH / 2, x1 - (x1 - x0) * 0.4, y1 - flowH / 2, x1, y1 - flowH / 2);
      ctx.lineTo(x1, y1 + flowH / 2);
      ctx.bezierCurveTo(x1 - (x1 - x0) * 0.4, y1 + flowH / 2, x0 + (x1 - x0) * 0.4, y0 + flowH / 2, x0, y0 + flowH / 2);
      ctx.closePath();
      ctx.fillStyle = color + "40";
      ctx.fill();
      ctx.strokeStyle = color + "80";
      ctx.lineWidth = 0.5;
      ctx.stroke();
    }

    // Draw source nodes
    for (const [ip, node] of srcNodes) {
      ctx.fillStyle = "#f59e0b";
      ctx.fillRect(leftX, node.y, nodeW, node.h);
      ctx.font = "10px monospace";
      ctx.fillStyle = "#e2e8f0";
      ctx.textAlign = "right";
      ctx.fillText(ip, leftX - 5, node.y + node.h / 2 + 3);
    }

    // Draw destination nodes
    for (const [host, node] of dstNodes) {
      ctx.fillStyle = "#3b82f6";
      ctx.fillRect(rightX, node.y, nodeW, node.h);
      ctx.font = "10px monospace";
      ctx.fillStyle = "#e2e8f0";
      ctx.textAlign = "left";
      const label = host.length > 25 ? host.slice(0, 22) + "..." : host;
      ctx.fillText(label, rightX + nodeW + 5, node.y + node.h / 2 + 3);
    }

    // Legend
    ctx.font = "10px sans-serif";
    ctx.textAlign = "left";
    const kinds = ["dns", "tls", "mdns"];
    let lx = w / 2 - 60;
    for (const k of kinds) {
      ctx.fillStyle = kindColor[k];
      ctx.fillRect(lx, 8, 10, 10);
      ctx.fillStyle = "#94a3b8";
      ctx.fillText(k.toUpperCase(), lx + 14, 17);
      lx += 55;
    }

    // Column labels
    ctx.font = "bold 11px sans-serif";
    ctx.fillStyle = "#64748b";
    ctx.textAlign = "center";
    ctx.fillText("DEVICES", leftX + nodeW / 2, pad.top - 15);
    ctx.fillText("DESTINATIONS", rightX + nodeW / 2, pad.top - 15);
  }, [flows]);

  useEffect(() => {
    const id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [draw, flows]);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Traffic Flow
      </h3>
      <canvas ref={canvasRef} className="h-[300px] w-full" />
    </div>
  );
}
