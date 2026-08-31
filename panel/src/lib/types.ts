export interface TrafficEvent {
  t: number;
  dev: string;
  kind: "dns" | "tls" | "mdns";
  host: string;
}

export interface DomainInfo {
  count: number;
  first: number;
  last: number;
  kinds: Record<string, number>;
  devs: Record<string, number>;
}

export interface TrafficDevice {
  count: number;
  first: number;
  last: number;
  n_domains: number;
  domains: Record<string, number>;
  protocols: Record<string, number>;
}

export interface TrafficState {
  updated: number;
  iface: string;
  packets: number;
  events: TrafficEvent[];
  domains: Record<string, DomainInfo>;
  devices: Record<string, TrafficDevice>;
}

export interface DeviceInfo {
  ip: string;
  mac: string;
  vendor: string;
  hostname: string;
  interface: string;
  first_seen: number;
  last_seen: number;
  online: boolean;
  traffic_events: number;
  domains: Record<string, number>;
  protocols: Record<string, number>;
  device_type?: string;
  device_model?: string;
  device_icon?: string;
  services?: Record<string, number>;
  urls?: Array<{ url: string; t: number; service?: string }>;
}

export interface DevicesState {
  updated: number;
  iface: string;
  count: number;
  devices: Record<string, DeviceInfo>;
}

export interface MergedDevice extends DeviceInfo {
  activity_level: "high" | "medium" | "low" | "idle";
}
