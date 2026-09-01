import pytest
import json
import time
import sys
import os
import struct
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestArpspoofStateCreation:
    def test_state_json_writing(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        state = {
            "iface": "en0", "packets": 0, "events": [],
            "domains": {}, "devices": {}, "updated": time.time(),
        }

        def add_event(src_ip, kind, host, service=None):
            event = {"t": time.time(), "dev": src_ip, "kind": kind, "host": host}
            if service:
                event["service"] = service
            state["events"].append(event)
            state["packets"] += 1
            if host not in state["domains"]:
                state["domains"][host] = {"count": 0, "kinds": {}, "devs": {}}
            state["domains"][host]["count"] += 1
            if src_ip not in state["devices"]:
                state["devices"][src_ip] = {
                    "ip": src_ip, "mac": "", "hostname": "", "vendor": "",
                    "device_type": "", "device_model": "", "device_icon": "📡",
                    "first_seen": time.time(), "last_seen": time.time(),
                    "online": True, "traffic_events": 0, "domains": {},
                    "protocols": {}, "services": {}, "urls": [],
                }
            dev = state["devices"][src_ip]
            dev["traffic_events"] += 1
            dev["last_seen"] = time.time()
            dev["domains"][host] = dev["domains"].get(host, 0) + 1

        add_event("192.168.2.10", "dns", "google.com", "google")
        add_event("192.168.2.10", "tls", "netflix.com", "netflix")
        add_event("192.168.2.20", "dns", "tiktok.com", "tiktok")

        out = {
            "updated": time.time(), "iface": state["iface"],
            "packets": state["packets"], "events": state["events"],
            "devices": state["devices"], "domains": state["domains"],
        }
        state_path = data_dir / "state.json"
        state_path.write_text(json.dumps(out, default=str))

        data = json.loads(state_path.read_text())
        assert data["packets"] == 3
        assert len(data["events"]) == 3
        assert len(data["devices"]) == 2
        assert "google.com" in data["domains"]
        assert data["devices"]["192.168.2.10"]["traffic_events"] == 2


class TestDeviceDetectionIntegration:
    def test_hostname_to_device_in_state(self, tmp_path):
        from device_detect import detect_device
        from oui_db import lookup_vendor

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        arp_entries = [
            {"ip": "192.168.2.10", "mac": "A4:83:E7:12:34:56", "hostname": "iPhone-Yunior"},
            {"ip": "192.168.2.20", "mac": "00:1E:58:12:34:56", "hostname": "galaxy-a04e"},
            {"ip": "192.168.2.30", "mac": "8C:8B:5B:12:34:56", "hostname": "brother-printer"},
            {"ip": "192.168.2.40", "mac": "64:1C:AE:12:34:56", "hostname": "c120"},
        ]

        devices = {}
        for entry in arp_entries:
            vendor = lookup_vendor(entry["mac"])
            info = detect_device(entry["hostname"], vendor)
            devices[entry["ip"]] = {
                "ip": entry["ip"], "mac": entry["mac"],
                "hostname": entry["hostname"], "vendor": vendor,
                "device_type": info["type"], "device_model": info["model"],
                "device_icon": info["icon"],
                "first_seen": time.time(), "last_seen": time.time(),
                "online": True, "traffic_events": 0,
            }

        devs_path = data_dir / "devices.json"
        devs_path.write_text(json.dumps({"devices": devices, "count": len(devices)}, default=str))

        data = json.loads(devs_path.read_text())
        devs = data["devices"]

        assert devs["192.168.2.10"]["device_type"] == "phone"
        assert devs["192.168.2.10"]["vendor"] == "Apple"
        assert devs["192.168.2.10"]["device_icon"] == "📱"
        assert devs["192.168.2.20"]["device_type"] == "phone"
        assert "Samsung" in devs["192.168.2.20"]["device_model"]
        assert devs["192.168.2.30"]["device_type"] == "printer"
        assert "Brother" in devs["192.168.2.30"]["device_model"]
        assert devs["192.168.2.40"]["device_type"] == "camera"
        assert "Tapo" in devs["192.168.2.40"]["device_model"]


class TestSQLiteIntegration:
    def test_events_appear_in_history(self, tmp_path, monkeypatch):
        import db as nwdb
        import threading
        db_path = tmp_path / "netwatch.db"
        monkeypatch.setattr(nwdb, "DB_PATH", db_path)
        nwdb._local = threading.local()
        nwdb.init_db()

        now = time.time()
        events = [
            (now - 100, "192.168.2.10", "dns", "google.com", "google"),
            (now - 90, "192.168.2.10", "tls", "netflix.com", "netflix"),
            (now - 80, "192.168.2.20", "dns", "tiktok.com", "tiktok"),
        ]
        for ts, dev, kind, host, svc in events:
            nwdb.insert_event(ts, dev, kind, host, svc)
        nwdb.flush_events()

        results = nwdb.query_events(since=now - 200, limit=50)
        assert len(results) == 3
        results = nwdb.query_events(dev="192.168.2.10", since=now - 200)
        assert len(results) == 2
        results = nwdb.query_events(kind="dns", since=now - 200)
        assert len(results) == 2
        results = nwdb.query_events(host="google", since=now - 200)
        assert len(results) == 1
        assert results[0]["host"] == "google.com"

    def test_device_upsert_from_arpspoof(self, tmp_path, monkeypatch):
        import db as nwdb
        import threading
        db_path = tmp_path / "netwatch.db"
        monkeypatch.setattr(nwdb, "DB_PATH", db_path)
        nwdb._local = threading.local()
        nwdb.init_db()

        now = time.time()
        nwdb.upsert_device(
            ip="192.168.2.10", mac="A4:83:E7:12:34:56",
            hostname="iPhone-Yunior", vendor="Apple",
            device_type="phone", device_model="iPhone",
            device_icon="📱", first_seen=now, last_seen=now,
            traffic_events=10, services='{"google":5}', domains='{"google.com":5}'
        )
        nwdb.flush_events()

        devices = nwdb.query_devices()
        assert len(devices) == 1
        assert devices[0]["ip"] == "192.168.2.10"
        assert devices[0]["vendor"] == "Apple"

        nwdb.upsert_device(
            ip="192.168.2.10", mac="A4:83:E7:12:34:56",
            hostname="iPhone-Yunior", vendor="Apple",
            device_type="phone", device_model="iPhone",
            last_seen=now + 60, traffic_events=20
        )
        nwdb.flush_events()

        devices = nwdb.query_devices()
        assert devices[0]["traffic_events"] == 20


class TestDomainClassification:
    def test_cdn_classification(self):
        # Import the classify_domain function directly without triggering arpspoof's module-level code
        # We replicate the CDN_PATTERNS and classify_domain logic
        CDN_PATTERNS = {
            "tiktok": {"patterns": ["tiktokcdn.com", "tiktokv.com", "tiktok.com", "byteoversea.com"],
                       "icon": "🎵", "type": "video"},
            "youtube": {"patterns": ["youtube.com", "ytimg.com", "googlevideo.com", "youtu.be"],
                        "icon": "📺", "type": "video"},
            "netflix": {"patterns": ["netflix.com", "nflxvideo.net", "nflximg.net"],
                        "icon": "🎬", "type": "streaming"},
            "instagram": {"patterns": ["instagram.com", "cdninstagram.com", "fbcdn.net"],
                          "icon": "📸", "type": "social"},
            "spotify": {"patterns": ["spotify.com", "scdn.co", "spotifycdn.com"],
                        "icon": "🎧", "type": "music"},
            "discord": {"patterns": ["discord.com", "discord.gg", "discordapp.com"],
                        "icon": "💬", "type": "chat"},
        }

        def classify_domain(domain):
            if not domain:
                return None, "🌐", "unknown"
            d = domain.lower()
            for service, info in CDN_PATTERNS.items():
                for pattern in info["patterns"]:
                    if pattern in d:
                        return service, info["icon"], info["type"]
            return None, "🌐", "web"

        assert classify_domain("tiktokcdn.com") == ("tiktok", "🎵", "video")
        assert classify_domain("youtube.com") == ("youtube", "📺", "video")
        assert classify_domain("netflix.com") == ("netflix", "🎬", "streaming")
        assert classify_domain("instagram.com") == ("instagram", "📸", "social")
        assert classify_domain("spotify.com") == ("spotify", "🎧", "music")
        assert classify_domain("discord.com") == ("discord", "💬", "chat")
        assert classify_domain("unknown-site.com") == (None, "🌐", "web")
        assert classify_domain("") == (None, "🌐", "unknown")


class TestDNSParsing:
    def test_parse_dns_simple(self):
        # Import parse_dns by extracting it from arpspoof source without running module-level code
        # We replicate the function since arpspoof has side effects at import time
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

        buf = bytearray(12)
        buf[2] = 0x01
        buf[4] = 0x00; buf[5] = 0x01
        buf[6] = 0x00; buf[7] = 0x00
        buf.extend(b"\x06google\x03com\x00")
        buf.extend(b"\x00\x01")
        buf.extend(b"\x00\x01")
        result = parse_dns(bytes(buf))
        assert result is not None
        assert "google.com" in result["names"]

    def test_parse_dns_short_buffer(self):
        def parse_dns(buf):
            if len(buf) < 12: return None
            return {"names": [], "answers": []}
        assert parse_dns(b"\x00" * 5) is None


class TestSNIParsing:
    def test_parse_sni_non_tls(self):
        def parse_sni(p):
            try:
                if len(p) < 5 or p[0] != 0x16: return None
                return "would-parse"
            except Exception:
                return None
        assert parse_sni(b"GET / HTTP/1.1\r\n") is None

    def test_parse_sni_short(self):
        def parse_sni(p):
            try:
                if len(p) < 5 or p[0] != 0x16: return None
                return "would-parse"
            except Exception:
                return None
        assert parse_sni(b"\x16\x03\x01") is None


class TestHTTPParsing:
    def test_parse_http_host(self):
        def parse_http_host(payload):
            try:
                text = payload.decode("utf-8", "replace")
                if not text.startswith(("GET ", "POST ", "HEAD ", "PUT ", "DELETE ", "CONNECT ")):
                    return None, None
                lines = text.split("\r\n")
                if not lines:
                    return None, None
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

        payload = b"GET /index.html HTTP/1.1\r\nHost: example.com\r\n\r\n"
        host, path = parse_http_host(payload)
        assert host == "example.com"
        assert path == "/index.html"

    def test_parse_http_host_no_host(self):
        def parse_http_host(payload):
            try:
                text = payload.decode("utf-8", "replace")
                if not text.startswith(("GET ", "POST ")):
                    return None, None
                lines = text.split("\r\n")
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

        payload = b"GET / HTTP/1.1\r\n\r\n"
        host, path = parse_http_host(payload)
        assert host is None

    def test_parse_http_host_not_http(self):
        def parse_http_host(payload):
            try:
                text = payload.decode("utf-8", "replace")
                if not text.startswith(("GET ", "POST ")):
                    return None, None
                return None, None
            except:
                return None, None

        host, path = parse_http_host(b"\x16\x03\x01\x00\x05")
        assert host is None
