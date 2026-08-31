"use client";

import { useMemo } from "react";

interface GeoEntry {
  country: string;
  city: string;
  ip: string;
  count: number;
  flag: string;
}

// Simple IP → geolocation (placeholder for real GeoIP)
// In production, integrate with MaxMind GeoLite2 or ip-api.com
function ipToGeo(ip: string): { country: string; city: string; flag: string } {
  // Private IPs
  if (ip.startsWith("192.168.") || ip.startsWith("10.") || ip.startsWith("172.")) {
    return { country: "Local", city: "LAN", flag: "🏠" };
  }
  // Placeholder mapping for demo
  return { country: "Unknown", city: "External", flag: "🌍" };
}

interface GeoMapProps {
  events: Array<{ dev: string; host: string; kind: string }>;
  domains: Record<string, { kinds: Record<string, number> }>;
}

// Well-known service → country mapping (approximate HQ locations)
const SERVICE_GEO: Record<string, { country: string; city: string; flag: string }> = {
  "apple.com": { country: "US", city: "Cupertino", flag: "🇺🇸" },
  "google.com": { country: "US", city: "Mountain View", flag: "🇺🇸" },
  "youtube.com": { country: "US", city: "San Bruno", flag: "🇺🇸" },
  "github.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "x.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "twitter.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "netflix.com": { country: "US", city: "Los Gatos", flag: "🇺🇸" },
  "cloudflare.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "microsoft.com": { country: "US", city: "Redmond", flag: "🇺🇸" },
  "amazon.com": { country: "US", city: "Seattle", flag: "🇺🇸" },
  "facebook.com": { country: "US", city: "Menlo Park", flag: "🇺🇸" },
  "instagram.com": { country: "US", city: "Menlo Park", flag: "🇺🇸" },
  "whatsapp.com": { country: "US", city: "Menlo Park", flag: "🇺🇸" },
  "openai.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "chat.openai.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "anthropic.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "discord.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "slack.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "spotify.com": { country: "SE", city: "Stockholm", flag: "🇸🇪" },
  "reddit.com": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "wikipedia.org": { country: "US", city: "San Francisco", flag: "🇺🇸" },
  "duckduckgo.com": { country: "US", city: "Paoli", flag: "🇺🇸" },
  "tesla.com": { country: "US", city: "Austin", flag: "🇺🇸" },
  "nvidia.com": { country: "US", city: "Santa Clara", flag: "🇺🇸" },
  "amd.com": { country: "US", city: "Santa Clara", flag: "🇺🇸" },
  "intel.com": { country: "US", city: "Santa Clara", flag: "🇺🇸" },
  "samsung.com": { country: "KR", city: "Seoul", flag: "🇰🇷" },
  "huawei.com": { country: "CN", city: "Shenzhen", flag: "🇨🇳" },
  "xiaomi.com": { country: "CN", city: "Beijing", flag: "🇨🇳" },
  "alibaba.com": { country: "CN", city: "Hangzhou", flag: "🇨🇳" },
  "baidu.com": { country: "CN", city: "Beijing", flag: "🇨🇳" },
  "yandex.ru": { country: "RU", city: "Moscow", flag: "🇷🇺" },
  "vk.com": { country: "RU", city: "Moscow", flag: "🇷🇺" },
  "bbc.co.uk": { country: "GB", city: "London", flag: "🇬🇧" },
  "bbc.com": { country: "GB", city: "London", flag: "🇬🇧" },
  "lemonde.fr": { country: "FR", city: "Paris", flag: "🇫🇷" },
  "kia.com": { country: "KR", city: "Seoul", flag: "🇰🇷" },
  "hyundai.com": { country: "KR", city: "Seoul", flag: "🇰🇷" },
  "toyota.com": { country: "JP", city: "Toyota", flag: "🇯🇵" },
  "sony.com": { country: "JP", city: "Tokyo", flag: "🇯🇵" },
  "nintendo.com": { country: "JP", city: "Kyoto", flag: "🇯🇵" },
};

export default function GeoMap({ events, domains }: GeoMapProps) {
  const geoData = useMemo(() => {
    const map = new Map<string, GeoEntry>();

    for (const domain of Object.keys(domains)) {
      const geo = SERVICE_GEO[domain] || ipToGeo(domain);
      const key = `${geo.country}-${geo.city}`;
      if (!map.has(key)) {
        map.set(key, {
          country: geo.country,
          city: geo.city,
          ip: domain,
          count: 0,
          flag: geo.flag,
        });
      }
      map.get(key)!.count += Object.values(domains[domain].kinds || {}).reduce((a, b) => a + b, 0);
    }

    return Array.from(map.values())
      .sort((a, b) => b.count - a.count)
      .slice(0, 12);
  }, [domains]);

  const total = geoData.reduce((a, b) => a + b.count, 0) || 1;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Connection Destinations
      </h3>
      <div className="space-y-2">
        {geoData.map((g) => (
          <div key={`${g.country}-${g.city}`} className="flex items-center gap-2">
            <span className="text-base">{g.flag}</span>
            <div className="flex-1">
              <div className="flex items-baseline gap-1.5">
                <span className="text-xs font-medium text-slate-200">{g.city}</span>
                <span className="text-[10px] text-slate-500">{g.country}</span>
              </div>
              <div className="mt-0.5 h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-600 to-blue-500 transition-all duration-500"
                  style={{ width: `${(g.count / total) * 100}%` }}
                />
              </div>
            </div>
            <span className="w-10 text-right font-mono text-[10px] text-slate-500">
              {g.count}
            </span>
          </div>
        ))}
      </div>
      {geoData.length === 0 && (
        <div className="text-center text-xs text-slate-500">No external connections</div>
      )}
    </div>
  );
}
