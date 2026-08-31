"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { TrafficState, DevicesState } from "./types";

const SSE_URL = process.env.NEXT_PUBLIC_SSE_URL || "/api/events";
const POLL_FALLBACK_MS = 2000;

type LiveData = {
  traffic: TrafficState | null;
  devices: DevicesState | null;
  connected: boolean;
};

export function useLiveData(_pollMs: number): LiveData {
  const [traffic, setTraffic] = useState<TrafficState | null>(null);
  const [devices, setDevices] = useState<DevicesState | null>(null);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const reconnectRef = useRef<NodeJS.Timeout | null>(null);

  const handleMessage = useCallback((raw: string) => {
    try {
      const msg = JSON.parse(raw);
      if (msg.type === "state") {
        setTraffic({
          updated: msg.updated,
          iface: msg.iface,
          packets: msg.packets,
          events: (msg.events || []).map((e: Record<string, unknown>, i: number) => ({
            id: i,
            t: e.t as number,
            dev: e.dev as string,
            kind: e.kind as string,
            host: e.host as string,
          })),
          domains: msg.domains || {},
          devices: msg.devices || {},
        });
        setDevices({
          updated: msg.updated,
          iface: msg.iface,
          count: Object.keys(msg.devices || {}).length,
          devices: msg.devices || {},
        });
        setConnected(true);
      } else if (msg.type === "connected") {
        setConnected(true);
      }
    } catch {}
  }, []);

  const connectSSE = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
    }

    const es = new EventSource(SSE_URL);
    esRef.current = es;

    es.onmessage = (e) => {
      if (e.data) handleMessage(e.data);
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      esRef.current = null;
      // Reconnect after 3s
      reconnectRef.current = setTimeout(connectSSE, 3000);
    };
  }, [handleMessage]);

  useEffect(() => {
    connectSSE();

    // Fallback: if SSE never connects, poll HTTP
    const fallbackId = setInterval(async () => {
      if (connected) return; // SSE is working, stop polling
      try {
        const [tRes, dRes] = await Promise.all([
          fetch("/api/state", { cache: "no-store" }),
          fetch("/api/devices", { cache: "no-store" }),
        ]);
        if (tRes.ok) {
          const t = await tRes.json();
          setTraffic({
            ...t,
            events: (t.events || []).map((e: Record<string, unknown>, i: number) => ({
              id: i,
              t: e.t as number,
              dev: e.dev as string,
              kind: e.kind as string,
              host: e.host as string,
            })),
          });
        }
        if (dRes.ok) setDevices(await dRes.json());
        setConnected(true);
      } catch {}
    }, POLL_FALLBACK_MS);

    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      esRef.current?.close();
      clearInterval(fallbackId);
    };
  }, [connectSSE, connected]);

  return { traffic, devices, connected };
}
