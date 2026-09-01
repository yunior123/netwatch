import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from device_detect import detect_device


class TestAppleDevices:
    def test_iphone_hostname(self):
        r = detect_device("iphone", "Apple")
        assert r["type"] == "phone"
        assert "iPhone" in r["model"]
        assert r["icon"] == "📱"

    def test_iphone_prefix(self):
        r = detect_device("iphone-yunior", "Apple")
        assert r["type"] == "phone"
        assert "iPhone" in r["model"]

    def test_ipad_hostname(self):
        r = detect_device("ipad", "Apple")
        assert r["type"] == "tablet"
        assert "iPad" in r["model"]

    def test_macbook_hostname(self):
        r = detect_device("macbook-pro-de-yunior", "Apple")
        assert r["type"] == "laptop"
        assert "MacBook" in r["model"]
        assert r["icon"] == "💻"

    def test_apple_vendor_only(self):
        r = detect_device("", "Apple")
        assert r["type"] == "device"


class TestSamsungDevices:
    def test_galaxy_a04e(self):
        r = detect_device("galaxy-a04e", "Samsung")
        assert r["type"] == "phone"
        assert "Samsung Galaxy A04" in r["model"]
        assert r["icon"] == "📱"

    def test_galaxy_s24_ultra(self):
        r = detect_device("galaxy-s24-ultra", "Samsung")
        assert r["type"] == "phone"
        assert "Samsung" in r["model"]
        assert "S24" in r["model"]

    def test_samsung_vendor_only(self):
        r = detect_device("", "Samsung")
        assert r["type"] == "phone"
        assert "Samsung" in r["model"]
        assert r["icon"] == "📱"

    def test_s24_prefix(self):
        r = detect_device("s24-de-erasmo", "")
        assert r["type"] == "phone"
        assert "Samsung Galaxy S24" in r["model"]


class TestGooglePixel:
    def test_pixel_8(self):
        r = detect_device("pixel-8", "")
        assert r["type"] == "phone"
        assert "Google Pixel 8" in r["model"]
        assert r["icon"] == "📱"

    def test_pixel_7_pro(self):
        r = detect_device("pixel-7-pro", "")
        assert r["type"] == "phone"
        assert "Google Pixel 7" in r["model"]
        assert "PRO" in r["model"].upper()


class TestTVDevices:
    def test_firestick(self):
        r = detect_device("firestick-xxx", "")
        assert r["type"] == "tv"
        assert "Amazon Fire TV" in r["model"]
        assert r["icon"] == "📺"

    def test_hisense_roku_tv(self):
        r = detect_device("43hisenserokutv", "")
        assert r["type"] == "tv"
        assert "Hisense Roku TV" in r["model"]
        assert r["icon"] == "📺"

    def test_tcl_roku_tv(self):
        r = detect_device("40tclrokutv", "")
        assert r["type"] == "tv"
        assert "TCL Roku TV" in r["model"]

    def test_roku_generic(self):
        r = detect_device("roku-12345", "")
        assert r["type"] == "tv"
        assert "Roku" in r["model"]


class TestSmartDevices:
    def test_thermostat(self):
        r = detect_device("thermostat", "")
        assert r["type"] == "thermostat"
        assert "Thermostat" in r["model"]
        assert r["icon"] == "🌡️"

    def test_watch(self):
        r = detect_device("watch", "")
        assert r["type"] == "watch"
        assert "Smartwatch" in r["model"]
        assert r["icon"] == "⌚"

    def test_camera_c120(self):
        r = detect_device("c120", "")
        assert r["type"] == "camera"
        assert "Tapo Camera" in r["model"]
        assert r["icon"] == "📷"

    def test_echo(self):
        r = detect_device("echo-dot", "")
        assert r["type"] == "speaker"
        assert "Amazon Echo" in r["model"]

    def test_ring_camera(self):
        r = detect_device("ring-doorbell", "")
        assert r["type"] == "camera"
        assert "Ring Camera" in r["model"]


class TestPrinters:
    def test_brother_vendor(self):
        r = detect_device("brother", "Brother")
        assert r["type"] == "printer"
        assert "Brother Printer" in r["model"]
        assert r["icon"] == "🖨️"

    def test_brother_hostname(self):
        r = detect_device("hl-l2350dw", "")
        assert r["type"] == "printer"
        assert "Brother" in r["model"]


class TestNetworkDevices:
    def test_router_hostname(self):
        r = detect_device("router", "")
        assert r["type"] == "router"
        assert r["icon"] == "🌐"

    def test_gateway_hostname(self):
        r = detect_device("mynetwork-gateway", "")
        assert r["type"] == "router"


class TestGamingConsoles:
    def test_playstation(self):
        r = detect_device("ps5", "")
        assert r["type"] == "console"
        assert "PlayStation" in r["model"]
        assert r["icon"] == "🎮"

    def test_xbox(self):
        r = detect_device("xbox-series-x", "")
        assert r["type"] == "console"
        assert "Xbox" in r["model"]


class TestFallback:
    def test_empty_both(self):
        r = detect_device("", "")
        assert r["type"] == "device"
        assert "Unknown Device" in r["model"]
        assert r["icon"] == "📡"

    def test_unknown_hostname(self):
        r = detect_device("random-hostname-xyz", "")
        assert r["type"] == "device"
        assert r["icon"] == "📡"

    def test_vendor_fallback(self):
        r = detect_device("", "Espressif")
        assert r["type"] == "device"
        assert "Espressif" in r["model"]


class TestReturnStructure:
    def test_return_keys(self):
        r = detect_device("iphone", "Apple")
        assert "type" in r
        assert "model" in r
        assert "icon" in r
        assert "label" in r
        assert "category" in r

    def test_label_matches_model(self):
        r = detect_device("iphone", "Apple")
        assert r["label"] == r["model"]
