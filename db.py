#!/usr/bin/env python3
"""SQLite database for netwatch events — 30-day retention."""

import sqlite3
import time
import os
import threading
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "netwatch.db"
RETENTION_DAYS = 30

_local = threading.local()

def _conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
    return _local.conn

def init_db():
    c = _conn()
    c.executescript("""
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
    c.commit()

def insert_event(ts, dev, kind, host, service=None, content_type=None):
    c = _conn()
    c.execute("INSERT INTO events (ts, dev, kind, host, service, content_type) VALUES (?, ?, ?, ?, ?, ?)",
              (ts, dev, kind, host, service, content_type))
    # Commit in batches (caller should call flush_events periodically)
    if c.in_transaction:
        return
    c.commit()

def flush_events():
    _conn().commit()

def upsert_device(ip, mac="", hostname="", vendor="", device_type="",
                  device_model="", device_icon="📡", first_seen=None,
                  last_seen=None, traffic_events=0, services=None, domains=None):
    c = _conn()
    now = time.time()
    c.execute("""INSERT INTO devices (ip, mac, hostname, vendor, device_type, device_model,
                 device_icon, first_seen, last_seen, traffic_events, services, domains)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT(ip) DO UPDATE SET
                 mac=COALESCE(NULLIF(excluded.mac,''), devices.mac),
                 hostname=COALESCE(NULLIF(excluded.hostname,''), devices.hostname),
                 vendor=COALESCE(NULLIF(excluded.vendor,''), devices.vendor),
                 device_type=COALESCE(NULLIF(excluded.device_type,''), devices.device_type),
                 device_model=COALESCE(NULLIF(excluded.device_model,''), devices.device_model),
                 device_icon=COALESCE(NULLIF(excluded.device_icon,''), devices.device_icon),
                 last_seen=excluded.last_seen,
                 traffic_events=excluded.traffic_events,
                 services=excluded.services,
                 domains=excluded.domains""",
              (ip, mac, hostname, vendor, device_type, device_model, device_icon,
               first_seen or now, last_seen or now, traffic_events,
               services or "{}", domains or "{}"))

def upsert_domain(host, count=0, first_seen=None, last_seen=None,
                  service=None, content_type=None, devices=None):
    c = _conn()
    now = time.time()
    c.execute("""INSERT INTO domains (host, count, first_seen, last_seen, service, content_type, devices)
                 VALUES (?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT(host) DO UPDATE SET
                 count=domains.count + excluded.count,
                 last_seen=excluded.last_seen,
                 service=COALESCE(NULLIF(excluded.service,''), domains.service),
                 content_type=COALESCE(NULLIF(excluded.content_type,''), domains.content_type),
                 devices=excluded.devices""",
              (host, count, first_seen or now, last_seen or now,
               service, content_type, devices or "{}"))

def cleanup_old():
    cutoff = time.time() - (RETENTION_DAYS * 86400)
    c = _conn()
    c.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
    c.commit()

def query_events(dev=None, host=None, kind=None, service=None,
                 since=None, limit=100, offset=0):
    c = _conn()
    where = []
    params = []
    if dev:
        where.append("dev = ?")
        params.append(dev)
    if host:
        where.append("host LIKE ?")
        params.append(f"%{host}%")
    if kind:
        where.append("kind = ?")
        params.append(kind)
    if service:
        where.append("service = ?")
        params.append(service)
    if since:
        where.append("ts >= ?")
        params.append(since)
    w = " AND ".join(where) if where else "1=1"
    params.extend([limit, offset])
    rows = c.execute(f"SELECT * FROM events WHERE {w} ORDER BY ts DESC LIMIT ? OFFSET ?",
                     params).fetchall()
    return [dict(r) for r in rows]

def query_events_count(dev=None, host=None, kind=None, service=None, since=None):
    c = _conn()
    where = []
    params = []
    if dev:
        where.append("dev = ?")
        params.append(dev)
    if host:
        where.append("host LIKE ?")
        params.append(f"%{host}%")
    if kind:
        where.append("kind = ?")
        params.append(kind)
    if service:
        where.append("service = ?")
        params.append(service)
    if since:
        where.append("ts >= ?")
        params.append(since)
    w = " AND ".join(where) if where else "1=1"
    return c.execute(f"SELECT COUNT(*) FROM events WHERE {w}", params).fetchone()[0]

def query_devices(limit=50):
    c = _conn()
    rows = c.execute("SELECT * FROM devices ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def query_domains(limit=50, min_count=1):
    c = _conn()
    rows = c.execute("SELECT * FROM domains WHERE count >= ? ORDER BY count DESC LIMIT ?",
                     (min_count, limit)).fetchall()
    return [dict(r) for r in rows]

def get_stats():
    c = _conn()
    total = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    devices = c.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    domains = c.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
    oldest = c.execute("SELECT MIN(ts) FROM events").fetchone()[0]
    newest = c.execute("SELECT MAX(ts) FROM events").fetchone()[0]
    by_kind = {}
    for row in c.execute("SELECT kind, COUNT(*) as cnt FROM events GROUP BY kind"):
        by_kind[row["kind"]] = row["cnt"]
    by_service = {}
    for row in c.execute("SELECT service, COUNT(*) as cnt FROM events WHERE service IS NOT NULL GROUP BY service ORDER BY cnt DESC LIMIT 10"):
        by_service[row["service"]] = row["cnt"]
    return {
        "total_events": total,
        "total_devices": devices,
        "total_domains": domains,
        "oldest_event": oldest,
        "newest_event": newest,
        "by_kind": by_kind,
        "by_service": by_service,
        "db_size_mb": round(os.path.getsize(DB_PATH) / 1024 / 1024, 2) if DB_PATH.exists() else 0,
    }

init_db()
