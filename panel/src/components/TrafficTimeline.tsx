"use client";

import { useRef, useEffect, useCallback } from "react";

interface TrafficPoint {
  t: number;
  dns: number;
  tls: number;
  mdns: number;
  other: number;
}

interface TrafficTimelineProps {
  events: Array<{ t: number; kind: string }>;
}

export default function TrafficTimeline({ events }: TrafficTimelineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointsRef = useRef<TrafficPoint[]>([]);

  // Aggregate events into 5-second buckets
  useEffect(() => {
    if (events.length === 0) return;
    const buckets = new Map<number, TrafficPoint>();
    const now = Date.now() / 1000;
    const windowSec = 120; // 2 minutes
    const bucketSize = 5;

    // Initialize empty buckets
    for (let t = now - windowSec; t <= now; t += bucketSize) {
      const key = Math.floor(t / bucketSize) * bucketSize;
      if (!buckets.has(key)) {
        buckets.set(key, { t: key, dns: 0, tls: 0, mdns: 0, other: 0 });
      }
    }

    // Fill buckets
    for (const e of events) {
      const key = Math.floor(e.t / bucketSize) * bucketSize;
      if (!buckets.has(key)) continue;
      const b = buckets.get(key)!;
      switch (e.kind) {
        case "dns": b.dns++; break;
        case "tls": b.tls++; break;
        case "mdns": b.mdns++; break;
        default: b.other++;
      }
    }

    pointsRef.current = Array.from(buckets.values()).sort((a, b) => a.t - b.t);
  }, [events]);

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
    const pad = { top: 30, right: 10, bottom: 25, left: 40 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    // Clear
    ctx.fillStyle = "rgba(15, 23, 42, 0.95)";
    ctx.fillRect(0, 0, w, h);

    const points = pointsRef.current;
    if (points.length === 0) {
      ctx.fillStyle = "#64748b";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Waiting for traffic data...", w / 2, h / 2);
      return;
    }

    // Find max
    const maxVal = Math.max(1, ...points.map(p => p.dns + p.tls + p.mdns + p.other));

    // Y-axis labels
    ctx.fillStyle = "#64748b";
    ctx.font = "10px monospace";
    ctx.textAlign = "right";
    for (let i = 0; i <= 4; i++) {
      const val = Math.round((maxVal / 4) * i);
      const y = pad.top + plotH - (plotH * (i / 4));
      ctx.fillText(val.toString(), pad.left - 5, y + 3);
      ctx.strokeStyle = "rgba(51, 65, 85, 0.3)";
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(pad.left + plotW, y);
      ctx.stroke();
    }

    // X-axis labels
    ctx.textAlign = "center";
    const timeRange = points[points.length - 1].t - points[0].t;
    for (let i = 0; i < points.length; i += Math.max(1, Math.floor(points.length / 6))) {
      const x = pad.left + (i / (points.length - 1)) * plotW;
      const d = new Date(points[i].t * 1000);
      ctx.fillText(d.toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit" }), x, h - 5);
    }

    // Stacked area chart
    const colors = ["#3b82f6", "#10b981", "#f472b6", "#64748b"];
    const layers = ["dns", "tls", "mdns", "other"] as const;

    for (let li = layers.length - 1; li >= 0; li--) {
      ctx.beginPath();
      for (let i = 0; i < points.length; i++) {
        const x = pad.left + (i / (points.length - 1)) * plotW;
        let sum = 0;
        for (let j = 0; j <= li; j++) {
          sum += points[i][layers[j]];
        }
        const y = pad.top + plotH - (sum / maxVal) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      // Close the area
      ctx.lineTo(pad.left + plotW, pad.top + plotH);
      ctx.lineTo(pad.left, pad.top + plotH);
      ctx.closePath();
      ctx.fillStyle = colors[li] + "60";
      ctx.fill();

      // Line on top
      ctx.beginPath();
      for (let i = 0; i < points.length; i++) {
        const x = pad.left + (i / (points.length - 1)) * plotW;
        let sum = 0;
        for (let j = 0; j <= li; j++) {
          sum += points[i][layers[j]];
        }
        const y = pad.top + plotH - (sum / maxVal) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = colors[li];
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Legend
    const legendItems = ["DNS", "TLS", "MDNS", "Other"];
    const legendColors = colors;
    let lx = pad.left;
    ctx.font = "10px sans-serif";
    for (let i = 0; i < legendItems.length; i++) {
      ctx.fillStyle = legendColors[i];
      ctx.fillRect(lx, 8, 10, 10);
      ctx.fillStyle = "#94a3b8";
      ctx.textAlign = "left";
      ctx.fillText(legendItems[i], lx + 14, 17);
      lx += ctx.measureText(legendItems[i]).width + 24;
    }
  }, []);

  useEffect(() => {
    const id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [draw, events]);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Traffic Timeline
      </h3>
      <canvas ref={canvasRef} className="h-[200px] w-full" />
    </div>
  );
}
