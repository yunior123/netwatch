# netwatch

Live, local-only wifi activity panel. Captures DNS, mDNS and TLS SNI on
`en0`, discovers ALL devices on your network via ARP/DHCP/mDNS, and serves
a modern React/Next.js dark-mode dashboard.

No external services. No telemetry. No hardcoded values.

## Architecture

```
tcpdump (root)  -->  data/capture.pcap
                          |
                      parser.py  (DNS/mDNS/TLS SNI, pure python, 0 deps)
                          |
                      data/state.json  (atomic, events + domains + devices + protocols)
                          |
discover.py  ---->  data/devices.json  (ARP + DHCP + mDNS + traffic merge)
   |                       |
   v                       v
Next.js API  (/api/state + /api/devices)
   |
   v
React Panel  (auto-refresh, device cards, activity feed, top domains)
```

## Run

```bash
# Full stack (parser + discover + panel)
./netwatch.sh start

# With live packet capture (needs root)
sudo ./netwatch.sh start

# Open dashboard
open http://127.0.0.1:3000
```

## Configuration (env vars, zero hardcoding)

| Variable | Default | What it does |
|---|---|---|
| `NETWATCH_IFACE` | `en0` | Network interface to capture on |
| `NETWATCH_PORT` | `3000` | Next.js panel port |
| `NETWATCH_DISCOVER_INTERVAL` | `30` | Device scan interval (seconds) |
| `NETWATCH_PING_TIMEOUT` | `1` | Ping timeout per host (seconds) |
| `NEXT_PUBLIC_POLL_MS` | `2000` | UI refresh interval (ms) |

## What the panel shows

- **Devices on Network** — every device found via ARP, DHCP, mDNS, and traffic.
  Cards with hostname, IP, MAC, activity level, and top domains contacted.
  Click any card for full detail.
- **Live Events** — last 200 events (`dns` / `tls` / `mdns`), newest first,
  with kind badges and filtering.
- **Top Domains** — sorted by count, with proportional bars, kind breakdown,
  and expandable per-domain detail (which devices hit it).
- **Device Detail** — click a device card to see IP, MAC, hostname, interface,
  traffic events, domains contacted, first/last seen.
- **Live filter** — filter by host, device, IP, or kind across all panels.
- **Auto-refresh** — polls every 2s (configurable), no manual reload needed.

## Device Discovery

`discover.py` runs every 30s and merges three sources:

1. **ARP table** (`arp -a`) — all devices that have communicated on the interface
2. **DHCP leases** (`/var/db/dhcpd_leases`) — devices with assigned IPs/hostnames
3. **Traffic data** (from parser) — devices generating DNS/mDNS/TLS traffic

This catches ALL devices: phones, tablets, laptops, smart TVs, IoT, even
devices that don't generate DNS traffic (like printers or cameras that only
use IP addresses).

## Self-test

```bash
python3 parser.py --selftest
```

## Demo without root

```bash
python3 scripts/synth_pcap.py
./netwatch.sh start
open http://127.0.0.1:3000
```

## Files

| File | Role |
|---|---|
| `netwatch.sh` | start / stop / status / restart orchestrator |
| `parser.py` | pcap tail, DNS/mDNS/TLS SNI parser, atomic state writer |
| `discover.py` | ARP/DHCP/mDNS device discovery, merges traffic data |
| `server.py` | Legacy Python server (fallback if no panel/) |
| `panel/` | Next.js React dashboard |
| `scripts/synth_pcap.py` | Synthetic pcap for no-root demo |
| `data/state.json` | Live traffic state (atomic writes) |
| `data/devices.json` | Device inventory (atomic writes) |
| `data/*.pid` | Process PIDs |
| `data/*.log` | Service logs |
