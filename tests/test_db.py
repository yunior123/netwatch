import pytest
import sqlite3
import time
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def db_module(tmp_path, monkeypatch):
    """Import db module with a temporary DB_PATH."""
    import importlib
    import db as nwdb
    db_path = tmp_path / "netwatch.db"
    monkeypatch.setattr(nwdb, "DB_PATH", db_path)
    # Reset thread-local connection
    nwdb._local = threading.local()
    nwdb.init_db()
    return nwdb


class TestInitDb:
    def test_creates_tables(self, db_module):
        """init_db() should create events, devices, domains tables."""
        conn = db_module._conn()
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "events" in tables
        assert "devices" in tables
        assert "domains" in tables

    def test_creates_indexes(self, db_module):
        """init_db() should create indexes on events."""
        conn = db_module._conn()
        indexes = {r[1] for r in conn.execute(
            "SELECT * FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        assert "idx_events_ts" in indexes
        assert "idx_events_dev" in indexes
        assert "idx_events_host" in indexes


class TestInsertEvent:
    def test_insert_stores_event(self, db_module):
        """insert_event() should store an event row."""
        now = time.time()
        db_module.insert_event(now, "192.168.2.10", "dns", "google.com", "google")
        db_module.flush_events()
        rows = db_module.query_events()
        assert len(rows) == 1
        assert rows[0]["dev"] == "192.168.2.10"
        assert rows[0]["kind"] == "dns"
        assert rows[0]["host"] == "google.com"
        assert rows[0]["service"] == "google"

    def test_insert_with_content_type(self, db_module):
        """insert_event() should store content_type."""
        now = time.time()
        db_module.insert_event(now, "192.168.2.10", "http", "example.com", content_type="text/html")
        db_module.flush_events()
        rows = db_module.query_events()
        assert rows[0]["content_type"] == "text/html"

    def test_insert_multiple(self, db_module):
        """Multiple inserts should all be stored."""
        now = time.time()
        for i in range(10):
            db_module.insert_event(now + i, "192.168.2.10", "dns", f"host{i}.com")
        db_module.flush_events()
        assert db_module.query_events_count() == 10


class TestFlushEvents:
    def test_flush_commits(self, db_module):
        """flush_events() should commit pending inserts."""
        now = time.time()
        db_module.insert_event(now, "192.168.2.10", "dns", "google.com")
        db_module.flush_events()
        # Should be visible after flush
        assert db_module.query_events_count() == 1


class TestUpsertDevice:
    def test_insert_new_device(self, db_module):
        """upsert_device() should insert a new device."""
        now = time.time()
        db_module.upsert_device("192.168.2.10", mac="AA:BB:CC:DD:EE:FF",
                                hostname="iPhone", vendor="Apple",
                                device_type="phone", first_seen=now, last_seen=now)
        db_module.flush_events()
        devices = db_module.query_devices()
        assert len(devices) == 1
        assert devices[0]["ip"] == "192.168.2.10"
        assert devices[0]["vendor"] == "Apple"

    def test_update_existing_device(self, db_module):
        """upsert_device() should update on conflict."""
        now = time.time()
        db_module.upsert_device("192.168.2.10", mac="AA:BB:CC:DD:EE:FF",
                                hostname="", vendor="Apple", first_seen=now, last_seen=now)
        db_module.flush_events()
        # Update hostname
        db_module.upsert_device("192.168.2.10", mac="AA:BB:CC:DD:EE:FF",
                                hostname="iPhone-Yunior", vendor="Apple",
                                last_seen=now + 100, traffic_events=5)
        db_module.flush_events()
        devices = db_module.query_devices()
        assert len(devices) == 1
        assert devices[0]["hostname"] == "iPhone-Yunior"
        assert devices[0]["traffic_events"] == 5

    def test_upsert_preserves_existing_hostname(self, db_module):
        """upsert_device() should not overwrite hostname with empty string."""
        now = time.time()
        db_module.upsert_device("192.168.2.10", hostname="iPhone", first_seen=now, last_seen=now)
        db_module.flush_events()
        db_module.upsert_device("192.168.2.10", hostname="", last_seen=now + 10)
        db_module.flush_events()
        devices = db_module.query_devices()
        assert devices[0]["hostname"] == "iPhone"


class TestUpsertDomain:
    def test_insert_new_domain(self, db_module):
        """upsert_domain() should insert a new domain."""
        now = time.time()
        db_module.upsert_domain("google.com", count=5, first_seen=now, last_seen=now,
                                service="google")
        db_module.flush_events()
        domains = db_module.query_domains()
        assert len(domains) == 1
        assert domains[0]["host"] == "google.com"
        assert domains[0]["count"] == 5

    def test_update_domain_accumulates_count(self, db_module):
        """upsert_domain() should add to existing count on conflict."""
        now = time.time()
        db_module.upsert_domain("google.com", count=5, first_seen=now, last_seen=now)
        db_module.flush_events()
        db_module.upsert_domain("google.com", count=3, last_seen=now + 10)
        db_module.flush_events()
        domains = db_module.query_domains()
        assert domains[0]["count"] == 8


class TestQueryEvents:
    def test_query_all(self, db_module):
        """query_events() with no filters should return all."""
        now = time.time()
        for i in range(5):
            db_module.insert_event(now + i, "192.168.2.10", "dns", f"host{i}.com")
        db_module.flush_events()
        assert len(db_module.query_events()) == 5

    def test_filter_by_dev(self, db_module):
        """query_events(dev=...) should filter by device."""
        now = time.time()
        db_module.insert_event(now, "192.168.2.10", "dns", "a.com")
        db_module.insert_event(now, "192.168.2.20", "dns", "b.com")
        db_module.flush_events()
        assert len(db_module.query_events(dev="192.168.2.10")) == 1

    def test_filter_by_host(self, db_module):
        """query_events(host=...) should filter by host pattern."""
        now = time.time()
        db_module.insert_event(now, "192.168.2.10", "dns", "google.com")
        db_module.insert_event(now, "192.168.2.10", "dns", "netflix.com")
        db_module.flush_events()
        results = db_module.query_events(host="google")
        assert len(results) == 1
        assert results[0]["host"] == "google.com"

    def test_filter_by_kind(self, db_module):
        """query_events(kind=...) should filter by event kind."""
        now = time.time()
        db_module.insert_event(now, "192.168.2.10", "dns", "a.com")
        db_module.insert_event(now, "192.168.2.10", "tls", "b.com")
        db_module.flush_events()
        assert len(db_module.query_events(kind="dns")) == 1

    def test_filter_by_service(self, db_module):
        """query_events(service=...) should filter by service."""
        now = time.time()
        db_module.insert_event(now, "192.168.2.10", "dns", "google.com", service="google")
        db_module.insert_event(now, "192.168.2.10", "dns", "other.com")
        db_module.flush_events()
        assert len(db_module.query_events(service="google")) == 1

    def test_filter_by_since(self, db_module):
        """query_events(since=...) should filter by timestamp."""
        now = time.time()
        db_module.insert_event(now - 1000, "192.168.2.10", "dns", "old.com")
        db_module.insert_event(now, "192.168.2.10", "dns", "new.com")
        db_module.flush_events()
        results = db_module.query_events(since=now - 100)
        assert len(results) == 1
        assert results[0]["host"] == "new.com"

    def test_limit(self, db_module):
        """query_events(limit=N) should limit results."""
        now = time.time()
        for i in range(10):
            db_module.insert_event(now + i, "192.168.2.10", "dns", f"h{i}.com")
        db_module.flush_events()
        assert len(db_module.query_events(limit=3)) == 3


class TestQueryEventsCount:
    def test_count_matches_query(self, db_module):
        """query_events_count() should match len(query_events())."""
        now = time.time()
        for i in range(7):
            db_module.insert_event(now + i, "192.168.2.10", "dns", f"h{i}.com")
        db_module.flush_events()
        assert db_module.query_events_count() == len(db_module.query_events(limit=1000))

    def test_count_with_filters(self, db_module):
        """query_events_count() with filters should match."""
        now = time.time()
        db_module.insert_event(now, "192.168.2.10", "dns", "google.com")
        db_module.insert_event(now, "192.168.2.20", "tls", "netflix.com")
        db_module.flush_events()
        assert db_module.query_events_count(dev="192.168.2.10") == 1
        assert db_module.query_events_count(kind="tls") == 1


class TestCleanupOld:
    def test_removes_old_events(self, db_module):
        """cleanup_old() should remove events older than 30 days."""
        now = time.time()
        old_ts = now - (31 * 86400)  # 31 days ago
        new_ts = now - (1 * 86400)   # 1 day ago
        db_module.insert_event(old_ts, "192.168.2.10", "dns", "old.com")
        db_module.insert_event(new_ts, "192.168.2.10", "dns", "new.com")
        db_module.flush_events()
        db_module.cleanup_old()
        rows = db_module.query_events(limit=100)
        assert len(rows) == 1
        assert rows[0]["host"] == "new.com"

    def test_keeps_recent_events(self, db_module):
        """cleanup_old() should keep events within 30 days."""
        now = time.time()
        db_module.insert_event(now - 86400, "192.168.2.10", "dns", "recent.com")
        db_module.flush_events()
        db_module.cleanup_old()
        assert db_module.query_events_count() == 1


class TestGetStats:
    def test_stats_counts(self, db_module):
        """get_stats() should return correct counts."""
        now = time.time()
        db_module.insert_event(now, "192.168.2.10", "dns", "google.com", "google")
        db_module.insert_event(now, "192.168.2.10", "tls", "netflix.com", "netflix")
        db_module.insert_event(now, "192.168.2.20", "dns", "tiktok.com", "tiktok")
        db_module.flush_events()
        stats = db_module.get_stats()
        assert stats["total_events"] == 3
        assert stats["by_kind"]["dns"] == 2
        assert stats["by_kind"]["tls"] == 1

    def test_stats_empty_db(self, db_module):
        """get_stats() on empty DB should return zeros."""
        stats = db_module.get_stats()
        assert stats["total_events"] == 0
        assert stats["total_devices"] == 0
        assert stats["total_domains"] == 0
        assert stats["oldest_event"] is None
        assert stats["newest_event"] is None


class TestThreadSafety:
    def test_concurrent_inserts(self, db_module):
        """Concurrent inserts from multiple threads should not crash."""
        errors = []

        def insert_batch(thread_id):
            try:
                now = time.time()
                for i in range(20):
                    db_module.insert_event(
                        now + i, f"192.168.2.{thread_id}", "dns", f"host-{thread_id}-{i}.com"
                    )
                db_module.flush_events()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=insert_batch, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All events should be stored (may vary due to thread-local connections)
        assert db_module.query_events_count() > 0
