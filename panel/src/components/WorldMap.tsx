"use client";

import { useRef, useEffect, useCallback } from "react";

// Simple world map coordinates (lat/lng to canvas x/y)
// Using Mercator-like projection
function latLngToXY(lat: number, lng: number, w: number, h: number): [number, number] {
  const x = ((lng + 180) / 360) * w;
  const latRad = (lat * Math.PI) / 180;
  const mercN = Math.log(Math.tan(Math.PI / 4 + latRad / 2));
  const y = h / 2 - (mercN / Math.PI) * (h / 2) * 0.8;
  return [x, y];
}

// Known service locations (approximate HQ coordinates)
const SERVICE_GEO: Record<string, { lat: number; lng: number; city: string; flag: string }> = {
  "apple.com": { lat: 37.32, lng: -122.03, city: "Cupertino", flag: "🇺🇸" },
  "google.com": { lat: 37.42, lng: -122.08, city: "Mountain View", flag: "🇺🇸" },
  "youtube.com": { lat: 37.42, lng: -122.08, city: "San Bruno", flag: "🇺🇸" },
  "github.com": { lat: 37.77, lng: -122.42, city: "San Francisco", flag: "🇺🇸" },
  "x.com": { lat: 37.77, lng: -122.42, city: "San Francisco", flag: "🇺🇸" },
  "netflix.com": { lat: 37.22, lng: -121.98, city: "Los Gatos", flag: "🇺🇸" },
  "cloudflare.com": { lat: 37.77, lng: -122.42, city: "San Francisco", flag: "🇺🇸" },
  "microsoft.com": { lat: 47.64, lng: -122.13, city: "Redmond", flag: "🇺🇸" },
  "amazon.com": { lat: 47.60, lng: -122.33, city: "Seattle", flag: "🇺🇸" },
  "facebook.com": { lat: 37.48, lng: -122.17, city: "Menlo Park", flag: "🇺🇸" },
  "openai.com": { lat: 37.77, lng: -122.42, city: "San Francisco", flag: "🇺🇸" },
  "chat.openai.com": { lat: 37.77, lng: -122.42, city: "San Francisco", flag: "🇺🇸" },
  "discord.com": { lat: 37.77, lng: -122.42, city: "San Francisco", flag: "🇺🇸" },
  "spotify.com": { lat: 59.33, lng: 18.07, city: "Stockholm", flag: "🇸🇪" },
  "reddit.com": { lat: 37.77, lng: -122.42, city: "San Francisco", flag: "🇺🇸" },
  "samsung.com": { lat: 37.56, lng: 126.97, city: "Seoul", flag: "🇰🇷" },
  "huawei.com": { lat: 22.55, lng: 114.06, city: "Shenzhen", flag: "🇨🇳" },
  "xiaomi.com": { lat: 39.90, lng: 116.40, city: "Beijing", flag: "🇨🇳" },
  "baidu.com": { lat: 39.90, lng: 116.40, city: "Beijing", flag: "🇨🇳" },
  "yandex.ru": { lat: 55.75, lng: 37.62, city: "Moscow", flag: "🇷🇺" },
  "bbc.co.uk": { lat: 51.51, lng: -0.13, city: "London", flag: "🇬🇧" },
  "bbc.com": { lat: 51.51, lng: -0.13, city: "London", flag: "🇬🇧" },
  "lemonde.fr": { lat: 48.86, lng: 2.35, city: "Paris", flag: "🇫🇷" },
  "kia.com": { lat: 37.56, lng: 126.97, city: "Seoul", flag: "🇰🇷" },
  "hyundai.com": { lat: 37.56, lng: 126.97, city: "Seoul", flag: "🇰🇷" },
  "nvidia.com": { lat: 37.37, lng: -121.95, city: "Santa Clara", flag: "🇺🇸" },
  "amd.com": { lat: 37.37, lng: -121.95, city: "Santa Clara", flag: "🇺🇸" },
  "intel.com": { lat: 37.37, lng: -121.95, city: "Santa Clara", flag: "🇺🇸" },
  "duckduckgo.com": { lat: 39.96, lng: -75.79, city: "Paoli", flag: "🇺🇸" },
  "apple-tv-yuno.local": { lat: 37.32, lng: -122.03, city: "Cupertino", flag: "🇺🇸" },
  "iphone-yuno.local": { lat: 37.32, lng: -122.03, city: "Cupertino", flag: "🇺🇸" },
  "macbook-pro.local": { lat: 37.77, lng: -122.42, city: "San Francisco", flag: "🇺🇸" },
};

interface WorldMapProps {
  domains: Record<string, { count: number }>;
}

export default function WorldMap({ domains }: WorldMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Simplified continent outlines (very rough)
  const drawWorldMap = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.fillStyle = "rgba(15, 23, 42, 0.95)";
    ctx.fillRect(0, 0, w, h);

    // Draw grid lines
    ctx.strokeStyle = "rgba(51, 65, 85, 0.15)";
    ctx.lineWidth = 0.5;
    for (let lat = -60; lat <= 80; lat += 30) {
      ctx.beginPath();
      for (let lng = -180; lng <= 180; lng += 5) {
        const [x, y] = latLngToXY(lat, lng, w, h);
        if (lng === -180) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    for (let lng = -180; lng <= 180; lng += 30) {
      ctx.beginPath();
      for (let lat = -60; lat <= 80; lat += 5) {
        const [x, y] = latLngToXY(lat, lng, w, h);
        if (lat === -60) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    // Draw rough continent shapes (dots for land masses)
    const continents = [
      // North America
      ...Array.from({ length: 40 }, () => [45 + Math.random() * 20, -100 + Math.random() * 40]),
      // South America
      ...Array.from({ length: 20 }, () => [-15 + Math.random() * 30, -65 + Math.random() * 20]),
      // Europe
      ...Array.from({ length: 20 }, () => [45 + Math.random() * 15, 5 + Math.random() * 25]),
      // Africa
      ...Array.from({ length: 25 }, () => [5 + Math.random() * 30, 15 + Math.random() * 25]),
      // Asia
      ...Array.from({ length: 35 }, () => [30 + Math.random() * 25, 60 + Math.random() * 60]),
      // Australia
      ...Array.from({ length: 10 }, () => [-28 + Math.random() * 10, 120 + Math.random() * 20]),
    ];

    ctx.fillStyle = "rgba(51, 65, 85, 0.3)";
    for (const [lat, lng] of continents) {
      const [x, y] = latLngToXY(lat as number, lng as number, w, h);
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    }
  }, []);

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

    drawWorldMap(ctx, w, h);

    // Our approximate location (Toronto)
    const [homeX, homeY] = latLngToXY(43.65, -79.38, w, h);
    ctx.fillStyle = "#f59e0b";
    ctx.beginPath();
    ctx.arc(homeX, homeY, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#f59e0b";
    ctx.font = "bold 9px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("🏠 You", homeX + 8, homeY + 3);

    // Draw connections to services
    const connections = Object.entries(domains)
      .filter(([domain]) => SERVICE_GEO[domain])
      .map(([domain, info]) => ({
        domain,
        count: info.count,
        ...SERVICE_GEO[domain],
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);

    for (const conn of connections) {
      const [x, y] = latLngToXY(conn.lat, conn.lng, w, h);

      // Arc from home to destination
      ctx.beginPath();
      ctx.moveTo(homeX, homeY);
      // Curved line (quadratic bezier)
      const cpx = (homeX + x) / 2;
      const cpy = Math.min(homeY, y) - 30;
      ctx.quadraticCurveTo(cpx, cpy, x, y);

      const alpha = Math.min(0.8, 0.2 + conn.count * 0.1);
      ctx.strokeStyle = `rgba(59, 130, 246, ${alpha})`;
      ctx.lineWidth = 1 + conn.count * 0.3;
      ctx.stroke();

      // Destination dot
      ctx.fillStyle = "#3b82f6";
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();

      // Label
      ctx.fillStyle = "#e2e8f0";
      ctx.font = "8px monospace";
      ctx.textAlign = "center";
      ctx.fillText(`${conn.flag} ${conn.city}`, x, y - 8);
    }

    // Legend
    ctx.font = "10px sans-serif";
    ctx.textAlign = "left";
    ctx.fillStyle = "#64748b";
    ctx.fillText(`Showing ${connections.length} connection destinations`, 10, h - 10);
  }, [domains, drawWorldMap]);

  useEffect(() => {
    const id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [draw]);

  return (
    <div className="relative rounded-lg border border-slate-800 bg-slate-900/50 overflow-hidden">
      <div className="absolute left-3 top-3 z-10 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Connection Map
      </div>
      <canvas ref={canvasRef} className="h-[300px] w-full" />
    </div>
  );
}
