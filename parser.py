#!/usr/bin/env python3
# netwatch parser: lee capture.pcap incremental, extrae DNS queries + TLS SNI + mDNS,
# y publica state.json atomico. Python puro, sin dependencias.
import json, os, struct, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
PCAP = os.path.join(DATA, "capture.pcap")
STATE = os.path.join(DATA, "state.json")

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
        off += 1
        if ln == 0:
            if end is None: end = off
            break
        if off + ln > len(buf): break
        labels.append(buf[off:off + ln].decode("utf-8", "replace"))
        off += ln
    return ".".join(labels), end

def parse_dns(p):
    if len(p) < 12: return None
    qd, an = struct.unpack_from(">HH", p, 4)
    qr = bool(p[2] & 0x80)
    off, names, answers = 12, [], []
    for _ in range(min(qd, 10)):
        name, off = dns_name(p, off)
        if off is None or off + 4 > len(p): return None
        off += 4
        if name: names.append(name)
    for _ in range(min(an, 40)):
        _, off = dns_name(p, off)
        if off is None or off + 10 > len(p): break
        rtype, _c, _t, rdlen = struct.unpack_from(">HHIH", p, off); off += 10
        if off + rdlen > len(p): break
        if rtype == 12:
            tgt, _ = dns_name(p, off)
            if tgt: answers.append(tgt)
        off += rdlen
    return {"qr": qr, "names": names, "answers": answers}

def parse_sni(p):
    try:
        if len(p) < 5 or p[0] != 0x16: return None
        if len(p) < 9 or p[5] != 0x01: return None
        off = 9 + 2 + 32
        sid = p[off]; off += 1 + sid
        cs = struct.unpack_from(">H", p, off)[0]; off += 2 + cs
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
            off += elen
    except Exception:
        return None
    return None

def handle_packet(ts, pkt, agg):
    if len(pkt) < 14: return
    etype = struct.unpack_from(">H", pkt, 12)[0]
    off = 14
    if etype == 0x8100 and len(pkt) >= 18:
        etype = struct.unpack_from(">H", pkt, 16)[0]; off = 18
    proto = sport = dport = None
    v6 = False
    payload = None
    src = dst = None
    if etype == 0x0800 and len(pkt) >= off + 20:
        ihl = (pkt[off] & 0x0F) * 4
        proto = pkt[off + 9]
        src = ".".join(str(b) for b in pkt[off + 12:off + 16])
        dst = ".".join(str(b) for b in pkt[off + 16:off + 20])
        l4 = off + ihl
    elif etype == 0x86DD and len(pkt) >= off + 40:
        proto = pkt[off + 6]
        src = ":".join(f"{struct.unpack('>H', pkt[off+8+i:off+10+i])[0]:x}" for i in range(0, 16, 2))
        dst = ":".join(f"{struct.unpack('>H', pkt[off+24+i:off+26+i])[0]:x}" for i in range(0, 16, 2))
        l4 = off + 40; v6 = True
    else:
        return
    if proto == 17 and len(pkt) >= l4 + 8:
        sport, dport, ulen = struct.unpack_from(">HHH", pkt, l4)
        payload = pkt[l4 + 8:l4 + ulen] if l4 + ulen <= len(pkt) else pkt[l4 + 8:]
        if 53 in (sport, dport) or 5353 in (sport, dport):
            dns = parse_dns(payload)
            if not dns: return
            kind = "mdns" if 5353 in (sport, dport) else "dns"
            hosts = dns["names"] if not dns["qr"] else []
            if dns["qr"] and kind == "mdns":
                hosts = dns["answers"][:2]
            for h in hosts:
                emit(agg, ts, src, kind, h)
    elif proto == 6 and len(pkt) >= l4 + 20:
        sport, dport = struct.unpack_from(">HH", pkt, l4)
        doff = ((pkt[l4 + 12] & 0xF0) >> 4) * 4
        payload = pkt[l4 + doff:]
        if dport == 443 and payload:
            sni = parse_sni(payload)
            if sni and "." in sni:
                emit(agg, ts, src, "tls", sni)

def emit(agg, ts, src, kind, host):
    host = host.rstrip(".").lower()
    if not host or len(host) > 250: return
    agg["packets"] += 1
    agg["events"].append({"t": round(ts, 3), "dev": src, "kind": kind, "host": host})
    del agg["events"][:-400]
    d = agg["domains"].setdefault(host, {"count": 0, "first": ts, "last": ts, "kinds": {}, "devs": {}})
    d["count"] += 1; d["last"] = ts
    d["kinds"][kind] = d["kinds"].get(kind, 0) + 1
    d["devs"][src] = d["devs"].get(src, 0) + 1
    dev = agg["devices"].setdefault(src, {"count": 0, "first": ts, "last": ts, "domains": {}, "protocols": {}})
    dev["count"] += 1; dev["last"] = ts
    dev["domains"][host] = dev["domains"].get(host, 0) + 1
    dev["protocols"][kind] = dev["protocols"].get(kind, 0) + 1

def flush(agg):
    os.makedirs(DATA, exist_ok=True)
    out = {
        "updated": time.time(), "iface": agg["iface"],
        "packets": agg["packets"],
        "events": agg["events"][-200:],
        "domains": {k: {"count": v["count"], "first": v["first"], "last": v["last"],
                        "kinds": v["kinds"], "devs": v["devs"]} for k, v in agg["domains"].items()},
        "devices": {k: {"count": v["count"], "first": v["first"], "last": v["last"],
                        "n_domains": len(v["domains"]), "domains": v["domains"],
                        "protocols": v.get("protocols", {})} for k, v in agg["devices"].items()},
    }
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f: json.dump(out, f)
    os.rename(tmp, STATE)

def run(iface):
    agg = {"iface": iface, "packets": 0, "events": [], "domains": {}, "devices": {}}
    off = 24; last_flush = 0; endian = "<"
    while True:
        try:
            size = os.path.getsize(PCAP)
        except OSError:
            time.sleep(1); continue
        if size < 24:
            time.sleep(0.5); continue
        with open(PCAP, "rb") as f:
            magic = f.read(4)
            endian = ">" if magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d") else "<"
            f.seek(off)
            buf = f.read()
        pos = 0
        while pos + 16 <= len(buf):
            ts_s, ts_u, incl, _orig = struct.unpack_from(endian + "IIII", buf, pos)
            if pos + 16 + incl > len(buf): break
            pkt = buf[pos + 16:pos + 16 + incl]
            try: handle_packet(ts_s + ts_u / 1e6, pkt, agg)
            except Exception: pass
            pos += 16 + incl
        off += pos
        if time.time() - last_flush > 1.5:
            flush(agg); last_flush = time.time()
        time.sleep(0.4)

def selftest():
    dns = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01"
    r = parse_dns(dns)
    assert r and r["names"] == ["example.com"], r
    name, end = dns_name(dns, 12)
    assert name == "example.com" and end == 25
    # PTR con puntero
    md = b"\x00\x00\x84\x00" + b"\x00\x00\x00\x01\x00\x00\x00\x00"
    md += b"\x00\x00\x0c\x00\x01" + b"\x00\x00\x00\x78" + b"\x00\x0f" + b"\x07MacBook\x05local\x00"
    r2 = parse_dns(md)
    assert r2 and r2["answers"] and r2["answers"][0].lower() == "macbook.local", r2
    # ClientHello con SNI tls.peer.test
    sni = b"tls.peer.test"
    server_name = b"\x00\x00" + struct.pack(">H", len(sni) + 5) + struct.pack(">H", len(sni) + 3) + b"\x00" + struct.pack(">H", len(sni)) + sni
    exts = server_name
    ch_body = b"\x03\x03" + b"\x01" * 32 + b"\x00" + struct.pack(">H", 2) + b"\x13\x01" + b"\x01\x00" + struct.pack(">H", len(exts)) + exts
    hs = b"\x01" + struct.pack(">I", len(ch_body))[1:] + ch_body
    rec = b"\x16\x03\x01" + struct.pack(">H", len(hs)) + hs
    assert parse_sni(rec) == "tls.peer.test", parse_sni(rec)
    print("SELFTEST OK")

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); sys.exit(0)
    import subprocess as _sp
    iface = sys.argv[1] if len(sys.argv) > 1 else "en0"
    # --live mode: start tcpdump ourselves writing to capture.pcap, then tail it
    if "--live" in sys.argv:
        if not os.path.exists(PCAP):
            rm_old = _sp.Popen(["rm", "-f", PCAP])
            rm_old.wait()
        _sp.Popen([
            "tcpdump", "-i", iface, "-U", "-s", "512", "-n", "-w", PCAP,
            "port", "53", "or", "port", "443", "or", "port", "5353", "or", "port", "67", "or", "port", "68"
        ], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        import signal; signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        print(f"parser: live capture started on {iface}", file=sys.stderr)
    run(iface)
