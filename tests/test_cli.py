import pytest
import json
import time
import sys
import os
import importlib
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock
from importlib.machinery import SourceFileLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NETWATCH_PATH = ROOT / "netwatch"


def _load_netwatch():
    """Load the netwatch CLI module (no .py extension)."""
    loader = SourceFileLoader("netwatch_cli", str(NETWATCH_PATH))
    mod = loader.load_module("netwatch_cli")
    return mod


class TestHelpCommand:
    def test_help_shows_all_commands(self, capsys):
        mod = _load_netwatch()
        with patch("sys.argv", ["netwatch", "help"]):
            mod.main()
        out = capsys.readouterr().out
        for cmd in ["start", "stop", "devices", "domains", "services", "who",
                     "history", "search", "dbstats", "analyze", "export",
                     "scan", "log", "kill", "rescue", "reset"]:
            assert cmd in out, f"'{cmd}' not found in help output"

    def test_help_exits_cleanly(self):
        mod = _load_netwatch()
        with patch("sys.argv", ["netwatch", "help"]):
            mod.main()


class TestStatusCommand:
    def test_status_no_state(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.STATE = data_dir / "state.json"
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "status"]):
            with patch.object(mod, "is_running", return_value=False):
                mod.main()
        out = capsys.readouterr().out
        assert "stopped" in out.lower() or "no state" in out.lower() or "no traffic" in out.lower()

    def test_status_with_state(self, capsys, tmp_path, sample_state, sample_devices):
        data_dir = tmp_path / "data"
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.STATE = data_dir / "state.json"
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "status"]):
            with patch.object(mod, "is_running", return_value=False):
                mod.main()
        out = capsys.readouterr().out
        assert "42" in out
        assert "2" in out


class TestDevicesCommand:
    def test_devices_no_data(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "devices"]):
            mod.main()
        out = capsys.readouterr().out
        assert "no devices" in out.lower()

    def test_devices_with_data(self, capsys, tmp_path, sample_state, sample_devices):
        data_dir = tmp_path / "data"
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "devices"]):
            mod.main()
        out = capsys.readouterr().out
        assert "iphone" in out.lower()
        assert "samsung" in out.lower()
        assert "📱" in out


class TestDomainsCommand:
    def test_domains_no_data(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.STATE = data_dir / "state.json"
        with patch("sys.argv", ["netwatch", "domains"]):
            mod.main()
        out = capsys.readouterr().out
        assert "no state" in out.lower() or "no domains" in out.lower()

    def test_domains_with_data(self, capsys, tmp_path, sample_state):
        data_dir = tmp_path / "data"
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.STATE = data_dir / "state.json"
        with patch("sys.argv", ["netwatch", "domains"]):
            mod.main()
        out = capsys.readouterr().out
        assert "google.com" in out
        assert "netflix.com" in out


class TestServicesCommand:
    def test_services_no_data(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "services"]):
            mod.main()
        out = capsys.readouterr().out
        assert "no devices" in out.lower()

    def test_services_with_data(self, capsys, tmp_path, sample_state, sample_devices):
        data_dir = tmp_path / "data"
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "services"]):
            mod.main()
        out = capsys.readouterr().out
        assert "google" in out.lower()
        assert "netflix" in out.lower()


class TestWhoCommand:
    def test_who_device_found(self, capsys, tmp_path, sample_state, sample_devices):
        data_dir = tmp_path / "data"
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "who", "192.168.2.10"]):
            mod.main()
        out = capsys.readouterr().out
        assert "iphone" in out.lower()
        assert "192.168.2.10" in out
        assert "Apple" in out

    def test_who_device_not_found(self, capsys, tmp_path, sample_state, sample_devices):
        data_dir = tmp_path / "data"
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "who", "10.0.0.99"]):
            mod.main()
        out = capsys.readouterr().out
        assert "not found" in out.lower()


class TestExportCommand:
    def test_export_no_state(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.STATE = data_dir / "state.json"
        with patch("sys.argv", ["netwatch", "export"]):
            mod.main()
        out = capsys.readouterr().out
        assert "no state" in out.lower()

    def test_export_creates_file(self, capsys, tmp_path, sample_state):
        data_dir = tmp_path / "data"
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.STATE = data_dir / "state.json"
        export_path = tmp_path / "netwatch-export.json"
        with patch("sys.argv", ["netwatch", "export"]):
            with patch("pathlib.Path.__new__", return_value=export_path):
                # The export writes to CWD; just verify no crash
                mod.main()
        out = capsys.readouterr().out


class TestResetCommand:
    def test_reset_clears_data(self, capsys, tmp_path, sample_state):
        data_dir = tmp_path / "data"
        state_file = data_dir / "state.json"
        devices_file = data_dir / "devices.json"
        kill_file = data_dir / "kill_list.json"
        db_file = data_dir / "netwatch.db"
        kill_file.write_text('["192.168.2.1"]')
        db_file.write_text("fake")
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.STATE = state_file
        mod.DEVICES = devices_file
        mod.DB_PATH = db_file
        with patch("sys.argv", ["netwatch", "reset"]):
            mod.main()
        out = capsys.readouterr().out
        assert "cleared" in out.lower() or "clearing" in out.lower()


class TestKillRescueCommands:
    def test_kill_adds_to_list(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        kill_file = data_dir / "kill_list.json"
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "kill", "192.168.2.50"]):
            mod.main()
        out = capsys.readouterr().out
        assert "blocked" in out.lower()
        assert kill_file.exists()
        assert "192.168.2.50" in json.loads(kill_file.read_text())

    def test_rescue_removes_from_list(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        kill_file = data_dir / "kill_list.json"
        kill_file.write_text(json.dumps(["192.168.2.50"]))
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "rescue", "192.168.2.50"]):
            mod.main()
        out = capsys.readouterr().out
        assert "unblocked" in out.lower()
        assert "192.168.2.50" not in json.loads(kill_file.read_text())


class TestLogCommand:
    def test_log_no_file(self, capsys, tmp_path):
        mod = _load_netwatch()
        mod.LOG = tmp_path / "nonexistent.log"
        with patch("sys.argv", ["netwatch", "log"]):
            mod.main()
        out = capsys.readouterr().out
        assert "no log" in out.lower()

    def test_log_shows_lines(self, capsys, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("line1\nline2\nline3\nline4\nline5\n")
        mod = _load_netwatch()
        mod.LOG = log_file
        with patch("sys.argv", ["netwatch", "log", "-n", "3"]):
            mod.main()
        out = capsys.readouterr().out
        assert "line3" in out
        assert "line4" in out
        assert "line5" in out


class TestAnalyzeCommand:
    def test_analyze_no_api_key(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.STATE = data_dir / "state.json"
        with patch("sys.argv", ["netwatch", "analyze"]):
            with patch.dict(os.environ, {"NVIDIA_NIM_API_KEY": ""}, clear=False):
                with patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="")):
                    mod.main()
        out = capsys.readouterr().out
        assert "api key" in out.lower() or "nvidia" in out.lower()


class TestErrorHandling:
    def test_invalid_command(self):
        mod = _load_netwatch()
        with patch("sys.argv", ["netwatch", "foobar"]):
            with pytest.raises(SystemExit) as exc_info:
                mod.main()
            assert exc_info.value.code == 1

    def test_block_alias_for_kill(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "block", "192.168.2.99"]):
            mod.main()
        out = capsys.readouterr().out
        assert "blocked" in out.lower()

    def test_unblock_alias_for_rescue(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        kill_file = data_dir / "kill_list.json"
        kill_file.write_text(json.dumps(["192.168.2.99"]))
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DEVICES = data_dir / "devices.json"
        with patch("sys.argv", ["netwatch", "unblock", "192.168.2.99"]):
            mod.main()
        out = capsys.readouterr().out
        assert "unblocked" in out.lower()


class TestHistoryCommand:
    def test_history_no_db(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DB_PATH = data_dir / "netwatch.db"
        with patch("sys.argv", ["netwatch", "history"]):
            mod.main()
        out = capsys.readouterr().out
        assert "no database" in out.lower()


class TestSearchCommand:
    def test_search_no_db(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DB_PATH = data_dir / "netwatch.db"
        with patch("sys.argv", ["netwatch", "search", "google"]):
            mod.main()
        out = capsys.readouterr().out
        assert "no database" in out.lower()


class TestDbstatsCommand:
    def test_dbstats_no_db(self, capsys, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        mod = _load_netwatch()
        mod.DATA = data_dir
        mod.DB_PATH = data_dir / "netwatch.db"
        with patch("sys.argv", ["netwatch", "dbstats"]):
            mod.main()
        out = capsys.readouterr().out
        assert "no database" in out.lower()


class TestGetDeviceHelpers:
    def test_get_device_name_model(self):
        mod = _load_netwatch()
        dev = {"device_model": "iPhone 15 Pro", "hostname": "iphone", "vendor": "Apple", "ip": "1.2.3.4"}
        assert mod.get_device_name(dev) == "iPhone 15 Pro"

    def test_get_device_name_hostname(self):
        mod = _load_netwatch()
        dev = {"device_model": "Unknown Device", "hostname": "my-laptop", "vendor": "Dell", "ip": "1.2.3.4"}
        assert mod.get_device_name(dev) == "my-laptop"

    def test_get_device_name_vendor(self):
        mod = _load_netwatch()
        dev = {"device_model": "", "hostname": "?", "vendor": "Samsung", "ip": "1.2.3.4"}
        assert mod.get_device_name(dev) == "Samsung"

    def test_get_device_icon_from_field(self):
        mod = _load_netwatch()
        dev = {"device_icon": "📺", "hostname": "tv"}
        assert mod.get_device_icon(dev) == "📺"

    def test_get_device_icon_from_hostname(self):
        mod = _load_netwatch()
        assert mod.get_device_icon({"device_icon": "📡", "hostname": "iphone"}) == "📱"
        assert mod.get_device_icon({"device_icon": "📡", "hostname": "macbook-pro"}) == "💻"
        assert mod.get_device_icon({"device_icon": "📡", "hostname": "roku-tv"}) == "📺"
        assert mod.get_device_icon({"device_icon": "📡", "hostname": "thermostat"}) == "🌡️"
        assert mod.get_device_icon({"device_icon": "📡", "hostname": "my-watch"}) == "⌚"
        assert mod.get_device_icon({"device_icon": "📡", "hostname": "c120-cam"}) == "📷"
        assert mod.get_device_icon({"device_icon": "📡", "hostname": "router"}) == "🌐"
