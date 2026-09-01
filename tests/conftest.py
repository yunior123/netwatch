import pytest
import json
import time
import sqlite3
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_data(tmp_path):
    """Create a temporary data directory with state.json and devices.json."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_state(tmp_data):
    """Write a sample state.json and return its contents."""
    state = {
        "updated": time.time(),
        "iface": "en0",
        "packets": 42,
        "events": [
            {"t": time.time(), "dev": "192.168.2.10", "kind": "dns", "host": "google.com", "service": "google"},
            {"t": time.time(), "dev": "192.168.2.10", "kind": "tls", "host": "netflix.com", "service": "netflix"},
            {"t": time.time(), "dev": "192.168.2.20", "kind": "dns", "host": "tiktok.com", "service": "tiktok"},
        ],
        "domains": {
            "google.com": {"count": 10, "kinds": {"dns": 5, "tls": 5}, "devs": {"192.168.2.10": 10}, "service": "google"},
            "netflix.com": {"count": 5, "kinds": {"tls": 5}, "devs": {"192.168.2.10": 5}, "service": "netflix"},
            "tiktok.com": {"count": 3, "kinds": {"dns": 3}, "devs": {"192.168.2.20": 3}, "service": "tiktok"},
        },
        "devices": {
            "192.168.2.10": {
                "ip": "192.168.2.10", "mac": "AA:BB:CC:DD:EE:FF", "hostname": "iPhone-Yunior",
                "vendor": "Apple", "device_type": "phone", "device_model": "iPhone",
                "device_icon": "📱", "first_seen": time.time() - 3600, "last_seen": time.time(),
                "online": True, "traffic_events": 15, "domains": {"google.com": 10, "netflix.com": 5},
                "protocols": {"dns": 5, "tls": 10}, "services": {"google": 10, "netflix": 5}, "urls": [],
            },
            "192.168.2.20": {
                "ip": "192.168.2.20", "mac": "11:22:33:44:55:66", "hostname": "galaxy-a04e",
                "vendor": "Samsung", "device_type": "phone", "device_model": "Samsung Galaxy A04",
                "device_icon": "📱", "first_seen": time.time() - 1800, "last_seen": time.time(),
                "online": True, "traffic_events": 3, "domains": {"tiktok.com": 3},
                "protocols": {"dns": 3}, "services": {"tiktok": 3}, "urls": [],
            },
        },
    }
    (tmp_data / "state.json").write_text(json.dumps(state))
    return state


@pytest.fixture
def sample_devices(tmp_data, sample_state):
    """Write a sample devices.json and return its contents."""
    devs = {
        "updated": time.time(),
        "iface": "en0",
        "count": 2,
        "devices": sample_state["devices"],
    }
    (tmp_data / "devices.json").write_text(json.dumps(devs))
    return devs


@pytest.fixture
def sample_db(tmp_data):
    """Create a temporary SQLite database with sample data."""
    db_path = tmp_data / "netwatch.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            dev TEXT NOT NULL,
            kind TEXT NOT NULL,
            host TEXT NOT NULL,
            service TEXT,
            content_type TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
        CREATE INDEX IF NOT EXISTS idx_events_dev ON events(dev);
        CREATE INDEX IF NOT EXISTS idx_events_host ON events(host);
        CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
        CREATE INDEX IF NOT EXISTS idx_events_service ON events(service);

        CREATE TABLE IF NOT EXISTS devices (
            ip TEXT PRIMARY KEY,
            mac TEXT,
            hostname TEXT,
            vendor TEXT,
            device_type TEXT,
            device_model TEXT,
            device_icon TEXT,
            first_seen REAL,
            last_seen REAL,
            traffic_events INTEGER DEFAULT 0,
            services TEXT,
            domains TEXT
        );

        CREATE TABLE IF NOT EXISTS domains (
            host TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            first_seen REAL,
            last_seen REAL,
            service TEXT,
            content_type TEXT,
            devices TEXT
        );
    """)
    now = time.time()
    events = [
        (now - 100, "192.168.2.10", "dns", "google.com", "google", None),
        (now - 90, "192.168.2.10", "tls", "netflix.com", "netflix", None),
        (now - 80, "192.168.2.20", "dns", "tiktok.com", "tiktok", None),
        (now - 70, "192.168.2.10", "tls", "youtube.com", "youtube", None),
        (now - 60, "192.168.2.30", "http", "example.com", None, "text/html"),
        (now - 50, "192.1墈.2.10", "dns", "apple.com", "apple", None),
    ]
    # Fix the typo in the last event
    events[-1] = (now - 50, "192.168.2.10", "dns", "apple.com", "apple", None)
    conn.executemany("INSERT INTO events (ts, dev, kind, host, service, content_type) VALUES (?,?,?,?,?,?)", events)
    conn.execute("""INSERT INTO devices (ip, mac, hostname, vendor, device_type, device_model, device_icon, first_seen, last_seen, traffic_events, services, domains)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 ("192.168.2.10", "AA:BB:CC:DD:EE:FF", "iPhone-Yunior", "Apple", "phone", "iPhone", "📱",
                  now - 3600, now, 4, '{"google":2,"netflix":1,"youtube":1}', '{"google.com":2,"netflix.com":1}'))
    conn.execute("""INSERT INTO domains (host, count, first_seen, last_seen, service, content_type, devices)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 ("google.com", 10, now - 3600, now, "google", None, '{"192.168.2.10":10}'))
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_events():
    """Return a list of sample network events."""
    now = time.time()
    return [
        {"t": now - 100, "dev": "192.168.2.10", "kind": "dns", "host": "google.com", "service": "google"},
        {"t": now - 90, "dev": "192.168.2.10", "kind": "tls", "host": "netflix.com", "service": "netflix"},
        {"t": now - 80, "dev": "192.168.2.20", "kind": "dns", "host": "tiktok.com", "service": "tiktok"},
        {"t": now - 70, "dev": "192.168.2.10", "kind": "tls", "host": "youtube.com", "service": "youtube"},
        {"t": now - 60, "dev": "192.168.2.30", "kind": "http", "host": "example.com"},
    ]


@pytest.fixture
def sample_device_info():
    """Return sample device info dict."""
    return {
        "ip": "192.168.2.10",
        "mac": "AA:BB:CC:DD:EE:FF",
        "hostname": "iPhone-Yunior",
        "vendor": "Apple",
        "device_type": "phone",
        "device_model": "iPhone",
        "device_icon": "📱",
        "traffic_events": 15,
        "services": {"google": 10, "netflix": 5},
        "domains": {"google.com": 10, "netflix.com": 5},
    }
