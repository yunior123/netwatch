#!/usr/bin/env python3
"""Synthesize a tiny pcap with DNS + mDNS packets so the panel
can be exercised without root / tcpdump. Runs once, writes pcap, exits.
"""
import os, struct, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "capture.pcap")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

def pcap_global_header():
    return struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)

def pcap_record(ts, pkt):
    return struct.pack("<IIII", int(ts), int((ts % 1) * 1_000_000), len(pkt), len(pkt)) + pkt

def eth(etype, payload):
    return (b"\x02\x00\x00\x00\x00\x01" + b"\x02\x00\x00\x00\x00\x02"
            + struct.pack(">H", etype) + payload)

def ip_udp(src, dst, sport, dport, payload):
    ip = bytearray(20)
    ip[0] = 0x45
    total = 20 + 8 + len(payload)
    struct.pack_into(">HH", ip, 2, total, 0)
    ip[8] = 64; ip[9] = 17
    a = bytes(int(x) for x in src.split("."))
    b = bytes(int(x) for x in dst.split("."))
    ip[12:16] = a; ip[16:20] = b
    udp = struct.pack(">HHHH", sport, dport, 8 + len(payload), 0) + payload
    return bytes(ip) + udp

def dns_query(name):
    parts = name.encode().split(b".")
    q = b""
    for p in parts: q += bytes([len(p)]) + p
    q += b"\x00"
    hdr = struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)
    qst = q + struct.pack(">HH", 1, 1)
    return hdr + qst

def _enc(name):
    parts = name.encode().split(b".")
    return b"".join(bytes([len(p)]) + p for p in parts) + b"\x00"

def mdns_ptr(name):
    # mDNS PTR response: query for `name`, answer is a PTR (type 12) whose
    # rdata is the same instance name. Record must follow the standard
    # RR layout: type(H) class(H) ttl(I) rdlength(H) rdata.
    q = _enc(name)
    hdr = struct.pack(">HHHHHH", 0, 0x8400, 0, 1, 0, 0)  # ID, flags(response), qd, an, ns, ar
    ans = q + struct.pack(">HHIH", 12, 1, 4500, len(q)) + q
    return hdr + ans

def ip_tcp(src, dst, sport, dport, payload):
    ip = bytearray(20)
    ip[0] = 0x45
    struct.pack_into(">HH", ip, 2, 20 + 20 + len(payload), 0)
    ip[8] = 64; ip[9] = 6  # protocol = TCP
    ip[12:16] = bytes(int(x) for x in src.split("."))
    ip[16:20] = bytes(int(x) for x in dst.split("."))
    tcp = bytearray(20)
    struct.pack_into(">HH", tcp, 0, sport, dport)
    tcp[12] = 0x50  # data offset = 5 (20 bytes), no options
    tcp[13] = 0x08  # PSH
    return bytes(ip) + bytes(tcp) + payload

def tls_sni(host, sport=51000):
    # Build a TLS 1.2-style ClientHello whose Server Name Indication is `host`.
    sni = host.encode()
    server_name = (b"\x00\x00" + struct.pack(">H", len(sni) + 5)
                   + struct.pack(">H", len(sni) + 3) + b"\x00"
                   + struct.pack(">H", len(sni)) + sni)
    exts = server_name
    ch_body = (b"\x03\x03" + b"\x01" * 32 + b"\x00" + struct.pack(">H", 2)
               + b"\x13\x01" + b"\x01\x00" + struct.pack(">H", len(exts)) + exts)
    hs = b"\x01" + struct.pack(">I", len(ch_body))[1:] + ch_body
    rec = b"\x16\x03\x01" + struct.pack(">H", len(hs)) + hs
    return eth(0x0800, ip_tcp("192.168.2.42", "104.16.124.99", sport, 443, rec))

now = time.time()
pkts = []
DNS = ["apple.com", "google.com", "github.com", "x.com", "youtube.com",
       "chat.openai.com", "duckduckgo.com", "microsoft.com",
       "apple.com", "google.com", "x.com", "github.com"]
for i, dom in enumerate(DNS):
    pkts.append((now + i * 0.1,
                 eth(0x0800, ip_udp("192.168.2.42", "1.1.1.1", 51000 + i, 53, dns_query(dom)))))
for i, name in enumerate(["iPhone-Yuno.local", "Apple-TV-Yuno.local",
                          "MacBook-Pro.local"]):
    pkts.append((now + 2 + i * 0.1,
                 eth(0x0800, ip_udp("192.168.2.42", "224.0.0.251", 5353, 5353, mdns_ptr(name)))))

# TLS ClientHello packets with SNI, sent to a :443 listener.
TLS = ["www.kia.com", "kia.com", "cloudflare.com", "netflix.com", "tailscale.com", "apple.com"]
for i, host in enumerate(TLS):
    pkts.append((now + 4 + i * 0.1,
                 tls_sni(host, 51000 + i)))

with open(OUT, "wb") as f:
    f.write(pcap_global_header())
    for ts, p in pkts:
        f.write(pcap_record(ts, p))
print(f"wrote {len(pkts)} packets -> {OUT}")
