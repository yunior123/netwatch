#!/usr/bin/env python3
"""netwatch device discovery — scans local network via ARP, DHCP, mDNS,
and merges traffic data from parser. Writes devices.json atomically.
Python puro, zero dependencies."""
import json, os, re, subprocess, time, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
STATE = os.path.join(DATA, "state.json")
DEVICES = os.path.join(DATA, "devices.json")
DHCP_LEASES = "/var/db/dhcpd_leases"

# Add root to path for OUI lookup
sys.path.insert(0, ROOT)
from oui_db import lookup_vendor

IFACE = os.environ.get("NETWATCH_IFACE", "en0")
DISCOVER_INTERVAL = int(os.environ.get("NETWATCH_DISCOVER_INTERVAL", "30"))
PING_TIMEOUT = int(os.environ.get("NETWATCH_PING_TIMEOUT", "1"))


def get_local_network():
    """Detect local subnet from interface."""
    try:
        out = subprocess.check_output(
            ["ifconfig", IFACE], stderr=subprocess.DEVNULL, text=True
        )
        m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+(\S+)", out)
        if not m:
            return None, None
        ip, mask = m.group(1), m.group(2)
        ip_parts = [int(x) for x in ip.split(".")]
        mask_parts = [int(x, 16) if x.startswith("0x") else int(x) for x in mask.split(".")]
        net_parts = [ip_parts[i] & mask_parts[i] for i in range(4)]
        net = ".".join(str(x) for x in net_parts)
        # /24 assumption for home networks
        return net, ip
    except Exception:
        return None, None


def parse_dhcp_leases():
    """Parse macOS DHCP leases file."""
    devices = {}
    try:
        with open(DHCP_LEASES) as f:
            content = f.read()
    except (OSError, PermissionError):
        return devices

    current = {}
    for line in content.splitlines():
        line = line.strip()
        if line == "{":
            current = {}
        elif line == "}":
            ip = current.get("ip_address")
            mac = current.get("hw_address", "")
            if ip and mac:
                mac = mac.split(",")[-1].strip().upper()
                devices[ip] = {
                    "mac": mac,
                    "hostname": current.get("name", ""),
                    "source": "dhcp",
                }
            current = {}
        elif "=" in line:
            k, _, v = line.partition("=")
            current[k.strip()] = v.strip().rstrip(";")
    return devices


def parse_arp_table():
    """Parse arp -a output for all devices on interface."""
    devices = {}
    try:
        out = subprocess.check_output(
            ["arp", "-a", "-i", IFACE], stderr=subprocess.DEVNULL, text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return devices

    for line in out.splitlines():
        # format: hostname (ip) at mac on en0 ifscope [ethernet]
        m = re.match(
            r"(\S+)\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+(\S+)\s+on\s+(\S+)",
            line,
        )
        if m:
            hostname, ip, mac, iface = m.groups()
            if mac == "(incomplete)" or mac == "ff:ff:ff:ff:ff:ff":
                continue
            mac = mac.upper()
            devices[ip] = {
                "mac": mac,
                "hostname": hostname if hostname != "?" else "",
                "interface": iface,
                "source": "arp",
            }
    return devices


def ping_sweep(network):
    """Quick ping of common addresses to populate ARP cache."""
    if not network:
        return
    base = ".".join(network.split(".")[:-1])
    # Ping gateway + common IPs in parallel (fast, ~2s total)
    targets = [f"{base}.1"]  # gateway
    # Also ping broadcast-ish range for discovery
    for i in range(2, 20):
        targets.append(f"{base}.{i}")

    try:
        # macOS ping: -c count, -W timeout ms, -t ttl
        subprocess.run(
            ["ping", "-c", "1", "-W", str(PING_TIMEOUT * 1000), "-t", "2"]
            + targets[:10],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=PING_TIMEOUT * len(targets[:10]) + 5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def discover_mdns():
    """Discover mDNS/Bonjour services on the network."""
    devices = {}
    try:
        # dns-sd -B browses for services, but we just want to see what responds
        out = subprocess.check_output(
            ["dns-sd", "-B", "_services._dns-sd._udp", IFACE],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        for line in out.splitlines():
            # Look for IP addresses in output
            ips = re.findall(r"(\d+\.\d+\.\d+\.\d+)", line)
            for ip in ips:
                if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
                    devices.setdefault(ip, {"source": "mdns"})
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    return devices


def merge_devices(arp_data, dhcp_data, mdns_data, traffic_devices):
    """Merge all sources into a unified device map."""
    merged = {}

    # Start with ARP data (most complete for active devices)
    for ip, info in arp_data.items():
        mac = info.get("mac", "")
        merged[ip] = {
            "ip": ip,
            "mac": mac,
            "vendor": lookup_vendor(mac),
            "hostname": info.get("hostname", ""),
            "interface": info.get("interface", IFACE),
            "first_seen": time.time(),
            "last_seen": time.time(),
            "online": True,
            "traffic_events": 0,
            "domains": {},
            "protocols": {},
        }

    # Merge DHCP (adds hostnames for devices without ARP names)
    for ip, info in dhcp_data.items():
        if ip in merged:
            if not merged[ip]["hostname"] and info.get("hostname"):
                merged[ip]["hostname"] = info["hostname"]
            if not merged[ip]["mac"] and info.get("mac"):
                merged[ip]["mac"] = info["mac"]
                if not merged[ip].get("vendor"):
                    merged[ip]["vendor"] = lookup_vendor(info["mac"])
        else:
            mac = info.get("mac", "")
            merged[ip] = {
                "ip": ip,
                "mac": mac,
                "vendor": lookup_vendor(mac),
                "hostname": info.get("hostname", ""),
                "interface": IFACE,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "online": False,  # in DHCP but not in ARP = not currently connected
                "traffic_events": 0,
                "domains": {},
                "protocols": {},
            }

    # Merge mDNS (adds service info)
    for ip, info in mdns_data.items():
        if ip in merged:
            merged[ip]["online"] = True
            merged[ip]["last_seen"] = time.time()

    # Merge traffic data from parser (adds activity info)
    for ip, info in traffic_devices.items():
        if ip in merged:
            merged[ip]["traffic_events"] = info.get("count", 0)
            merged[ip]["domains"] = info.get("domains", {})
            merged[ip]["protocols"] = info.get("protocols", {})
            merged[ip]["last_seen"] = max(merged[ip]["last_seen"], info.get("last", 0))
            merged[ip]["first_seen"] = min(merged[ip]["first_seen"], info.get("first", time.time()))
        else:
            merged[ip] = {
                "ip": ip,
                "mac": "",
                "hostname": "",
                "interface": IFACE,
                "first_seen": info.get("first", time.time()),
                "last_seen": info.get("last", time.time()),
                "online": True,  # generating traffic = online
                "traffic_events": info.get("count", 0),
                "domains": info.get("domains", {}),
                "protocols": info.get("protocols", {}),
            }

    return merged


def read_parser_devices():
    """Read device data that parser.py wrote to state.json."""
    try:
        with open(STATE) as f:
            state = json.load(f)
        return state.get("devices", {})
    except (OSError, json.JSONDecodeError):
        return {}


def write_devices(devices):
    """Atomic write of devices.json."""
    os.makedirs(DATA, exist_ok=True)
    out = {
        "updated": time.time(),
        "iface": IFACE,
        "count": len(devices),
        "devices": devices,
    }
    tmp = DEVICES + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    os.rename(tmp, DEVICES)


def scan_once():
    """Single discovery scan cycle."""
    net, local_ip = get_local_network()

    # Quick ping to populate ARP cache
    if net:
        ping_sweep(net)

    arp = parse_arp_table()
    dhcp = parse_dhcp_leases()
    mdns = discover_mdns()
    traffic = read_parser_devices()

    devices = merge_devices(arp, dhcp, mdns, traffic)
    write_devices(devices)
    return devices


def run():
    """Main loop: scan every DISCOVER_INTERVAL seconds."""
    os.makedirs(DATA, exist_ok=True)
    print(f"discover: iface={IFACE} interval={DISCOVER_INTERVAL}s", flush=True)
    while True:
        try:
            devices = scan_once()
            print(f"discover: {len(devices)} devices", flush=True)
        except Exception as e:
            print(f"discover: error: {e}", flush=True)
        time.sleep(DISCOVER_INTERVAL)


if __name__ == "__main__":
    if "--once" in sys.argv:
        devices = scan_once()
        print(json.dumps(devices, indent=2))
    else:
        run()
