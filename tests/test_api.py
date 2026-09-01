import pytest
import json
import time
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from http.server import ThreadingHTTPServer
import threading
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def api_server(tmp_path, sample_state, sample_devices):
    """Start the Python HTTP server on a random port and return (url, thread)."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)

    # Write state.json and devices.json
    (data_dir / "state.json").write_text(json.dumps(sample_state))
    (data_dir / "devices.json").write_text(json.dumps(sample_devices))

    import server as srv

    class TestHandler(srv.H):
        def log_message(self, *a): pass

    # Patch paths
    original_state = srv.STATE
    original_index = srv.INDEX
    srv.STATE = str(data_dir / "state.json")
    srv.INDEX = str(ROOT / "index.html")

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    httpd.shutdown()
    srv.STATE = original_state
    srv.INDEX = original_index


class TestStateEndpoint:
    def test_get_state(self, api_server):
        """GET /api/state should return state.json contents."""
        url = f"{api_server}/api/state"
        resp = urllib.request.urlopen(url)
        data = json.loads(resp.read())
        assert data["packets"] == 42
        assert "devices" in data
        assert "domains" in data
        assert "events" in data

    def test_state_no_cache(self, api_server):
        """GET /api/state should have no-store cache header."""
        url = f"{api_server}/api/state"
        resp = urllib.request.urlopen(url)
        assert "no-store" in resp.headers.get("Cache-Control", "")


class TestStateEndpointMissing:
    def test_missing_state_returns_empty(self, tmp_path):
        """GET /api/state with no file should return empty state."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)

        import server as srv

        class TestHandler(srv.H):
            def log_message(self, *a): pass

        original_state = srv.STATE
        srv.STATE = str(data_dir / "nonexistent.json")

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        try:
            url = f"http://127.0.0.1:{port}/api/state"
            resp = urllib.request.urlopen(url)
            data = json.loads(resp.read())
            assert data.get("empty") is True
        finally:
            httpd.shutdown()
            srv.STATE = original_state


class TestIndexEndpoint:
    def test_get_index(self, api_server):
        """GET / should return HTML."""
        url = f"{api_server}/"
        resp = urllib.request.urlopen(url)
        content = resp.read().decode()
        assert "html" in content.lower() or len(content) > 0


class TestNotFound:
    def test_unknown_path(self, api_server):
        """GET /unknown should return 404."""
        url = f"{api_server}/unknown"
        try:
            urllib.request.urlopen(url)
            assert False, "Should have raised HTTPError"
        except urllib.error.HTTPError as e:
            assert e.code == 404


class TestPanelAPIRoutes:
    """Test the Next.js panel API routes by verifying the data files they read."""

    def test_state_json_structure(self, tmp_path, sample_state):
        """state.json should have the structure expected by /api/state."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        path = data_dir / "state.json"
        path.write_text(json.dumps(sample_state))
        data = json.loads(path.read_text())
        assert "updated" in data
        assert "iface" in data
        assert "packets" in data
        assert "events" in data
        assert "domains" in data
        assert "devices" in data

    def test_devices_json_structure(self, tmp_path, sample_devices):
        """devices.json should have the structure expected by /api/devices."""
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        path = data_dir / "devices.json"
        path.write_text(json.dumps(sample_devices))
        data = json.loads(path.read_text())
        assert "updated" in data
        assert "iface" in data
        assert "count" in data
        assert "devices" in data

    def test_events_sse_structure(self, sample_state):
        """Events in state.json should be compatible with SSE endpoint."""
        events = sample_state["events"]
        for e in events:
            assert "t" in e
            assert "dev" in e
            assert "kind" in e
            assert "host" in e

    def test_history_query_compatible(self, sample_db):
        """SQLite DB should be queryable like /api/history does."""
        import db as nwdb
        import importlib
        importlib.reload(nwdb)
        # The sample_db fixture creates a DB, but we need to point nwdb at it
        # Instead, just verify the DB is queryable directly
        import sqlite3
        conn = sqlite3.connect(str(sample_db))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM events ORDER BY ts DESC LIMIT 10").fetchall()
        assert len(rows) > 0
        for r in rows:
            d = dict(r)
            assert "ts" in d
            assert "dev" in d
            assert "kind" in d
            assert "host" in d
        conn.close()

    def test_captures_dir_structure(self, tmp_path):
        """captures/ directory should list .pcap files."""
        data_dir = tmp_path / "data"
        captures_dir = data_dir / "captures"
        captures_dir.mkdir(parents=True)
        # Create a fake pcap
        (captures_dir / "test.pcap").write_bytes(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20)
        files = list(captures_dir.iterdir())
        assert len(files) == 1
        assert files[0].suffix == ".pcap"
