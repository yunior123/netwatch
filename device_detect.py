#!/usr/bin/env python3
"""Device type + model detection from hostname, mDNS services, OUI vendor, and traffic.
Returns: { type, model, icon, label, vendor, category }
"""
import re

# ─── Apple model database (from mDNS model strings) ─────────────────
# Apple devices advertise model strings like "MacBook Pro (16-inch, 2021)"
# or "iPhone14,3" (identifier) in mDNS TXT records
APPLE_MODELS = {
    # iPhones — identifiers to marketing name
    "iPhone10,1": "iPhone 8", "iPhone10,2": "iPhone 8 Plus",
    "iPhone10,3": "iPhone X", "iPhone10,4": "iPhone 8",
    "iPhone10,5": "iPhone 8 Plus", "iPhone10,6": "iPhone X",
    "iPhone11,2": "iPhone XS", "iPhone11,4": "iPhone XS Max",
    "iPhone11,6": "iPhone XS Max", "iPhone11,8": "iPhone XR",
    "iPhone12,1": "iPhone 11", "iPhone12,3": "iPhone 11 Pro",
    "iPhone12,5": "iPhone 11 Pro Max", "iPhone12,8": "iPhone SE (2nd gen)",
    "iPhone13,1": "iPhone 12 mini", "iPhone13,2": "iPhone 12",
    "iPhone13,3": "iPhone 12 Pro", "iPhone13,4": "iPhone 12 Pro Max",
    "iPhone14,2": "iPhone 13 Pro", "iPhone14,3": "iPhone 13 Pro Max",
    "iPhone14,4": "iPhone 13 mini", "iPhone14,5": "iPhone 13",
    "iPhone14,6": "iPhone SE (3rd gen)", "iPhone14,7": "iPhone 14",
    "iPhone14,8": "iPhone 14 Plus", "iPhone15,2": "iPhone 14 Pro",
    "iPhone15,3": "iPhone 14 Pro Max", "iPhone15,4": "iPhone 15",
    "iPhone15,5": "iPhone 15 Plus", "iPhone16,1": "iPhone 15 Pro",
    "iPhone16,2": "iPhone 15 Pro Max", "iPhone17,1": "iPhone 16 Pro",
    "iPhone17,2": "iPhone 16 Pro Max", "iPhone17,3": "iPhone 16",
    "iPhone17,4": "iPhone 16 Plus",
    # iPads
    "iPad7,11": "iPad (7th gen)", "iPad7,12": "iPad (7th gen)",
    "iPad11,3": "iPad Pro 11-inch (1st gen)", "iPad11,4": "iPad Pro 11-inch (1st gen)",
    "iPad11,6": "iPad Pro 12.9-inch (3rd gen)", "iPad11,7": "iPad Pro 12.9-inch (3rd gen)",
    "iPad12,1": "iPad (8th gen)", "iPad12,2": "iPad (8th gen)",
    "iPad13,1": "iPad Air (4th gen)", "iPad13,2": "iPad Air (4th gen)",
    "iPad13,4": "iPad Pro 11-inch (3rd gen)", "iPad13,5": "iPad Pro 11-inch (3rd gen)",
    "iPad13,6": "iPad Pro 11-inch (3rd gen)", "iPad13,7": "iPad Pro 11-inch (3rd gen)",
    "iPad13,8": "iPad Pro 12.9-inch (5th gen)", "iPad13,9": "iPad Pro 12.9-inch (5th gen)",
    "iPad13,10": "iPad Pro 12.9-inch (5th gen)", "iPad13,11": "iPad Pro 12.9-inch (5th gen)",
    "iPad14,1": "iPad mini (6th gen)", "iPad14,2": "iPad mini (6th gen)",
    "iPad14,3": "iPad Pro 11-inch (4th gen)", "iPad14,4": "iPad Pro 11-inch (4th gen)",
    "iPad14,5": "iPad Pro 12.9-inch (6th gen)", "iPad14,6": "iPad Pro 12.9-inch (6th gen)",
    # Mac
    "MacBookPro16,1": "MacBook Pro 16-inch (2019)", "MacBookPro16,2": "MacBook Pro 13-inch (2020)",
    "MacBookPro16,3": "MacBook Pro 13-inch (2020)", "MacBookPro16,4": "MacBook Pro 16-inch (2020)",
    "MacBookPro17,1": "MacBook Pro 13-inch (M1, 2020)", "MacBookPro17,2": "MacBook Pro 13-inch (M1, 2020)",
    "MacBookPro18,1": "MacBook Pro 16-inch (2021)", "MacBookPro18,2": "MacBook Pro 16-inch (2021)",
    "MacBookPro18,3": "MacBook Pro 14-inch (2021)", "MacBookPro18,4": "MacBook Pro 14-inch (2021)",
    "MacBookAir10,1": "MacBook Air (M1, 2020)", "MacBookAir10,2": "MacBook Air (M1, 2020)",
    "Mac14,2": "MacBook Air (M2, 2022)", "Mac14,7": "MacBook Pro 13-inch (M2, 2022)",
    "Mac15,3": "MacBook Pro 14-inch (M3, 2023)", "Mac15,4": "MacBook Pro 14-inch (M3, 2023)",
    "Mac15,6": "MacBook Pro 16-inch (M3 Pro, 2023)", "Mac15,7": "MacBook Pro 16-inch (M3 Pro, 2023)",
    # Apple TV
    "AppleTV5,3": "Apple TV HD", "AppleTV6,2": "Apple TV 4K (1st gen)",
    "AppleTV11,1": "Apple TV 4K (2nd gen)", "AppleTV14,1": "Apple TV 4K (3rd gen)",
    # Watch
    "Watch3,1": "Apple Watch Series 3", "Watch3,2": "Apple Watch Series 3",
    "Watch4,1": "Apple Watch Series 4", "Watch4,2": "Apple Watch Series 4",
    "Watch4,3": "Apple Watch Series 4", "Watch4,4": "Apple Watch Series 4",
    "Watch5,1": "Apple Watch Series 5", "Watch5,2": "Apple Watch Series 5",
    "Watch5,3": "Apple Watch Series 5", "Watch5,4": "Apple Watch Series 5",
    "Watch6,1": "Apple Watch Series 6", "Watch6,2": "Apple Watch Series 6",
    "Watch6,3": "Apple Watch Series 7", "Watch6,4": "Apple Watch Series 7",
    "Watch6,5": "Apple Watch SE", "Watch6,6": "Apple Watch SE",
    "Watch6,7": "Apple Watch Series 8", "Watch6,8": "Apple Watch Series 8",
    "Watch6,9": "Apple Watch Ultra", "Watch6,10": "Apple Watch Ultra",
    "Watch7,1": "Apple Watch Series 9", "Watch7,2": "Apple Watch Series 9",
    "Watch7,3": "Apple Watch Ultra 2", "Watch7,4": "Apple Watch Ultra 2",
    "Watch7,5": "Apple Watch Series 10", "Watch7,6": "Apple Watch Series 10",
    # HomePod
    "AudioAccessory1,1": "HomePod", "AudioAccessory1,2": "HomePod mini",
    "AudioAccessory5,1": "HomePod (2nd gen)",
}

# ─── Samsung Galaxy model patterns ──────────────────────────────────
SAMSUNG_GALAXY = [
    # Galaxy S series
    (r"galaxy[- ]?s(\d{2})", "Samsung Galaxy S{}", "phone"),
    (r"sm-[sg](\d{3,4})", "Samsung Galaxy (SM-{})", "phone"),
    # Galaxy Note
    (r"galaxy[- ]?note(\d+)", "Samsung Galaxy Note{}", "phone"),
    # Galaxy Z Fold/Flip
    (r"galaxy[- ]?z[ -]?fold(\d+)", "Samsung Galaxy Z Fold {}", "phone"),
    (r"galaxy[- ]?z[ -]?flip(\d+)", "Samsung Galaxy Z Flip {}", "phone"),
    # Galaxy A/M series
    (r"galaxy[- ]?a(\d{2,3})", "Samsung Galaxy A{}", "phone"),
    (r"galaxy[- ]?m(\d{2,3})", "Samsung Galaxy M{}", "phone"),
    # Galaxy Tab
    (r"galaxy[- ]?tab[ -]?s(\d+)", "Samsung Galaxy Tab S{}", "tablet"),
    (r"galaxy[- ]?tab[ -]?a(\d+)", "Samsung Galaxy Tab A{}", "tablet"),
    # Generic
    (r"galaxy[- ]?s\d+[ -]?ultra", "Samsung Galaxy S Ultra", "phone"),
    (r"galaxy[- ]?s\d+[ -]?plus", "Samsung Galaxy S Plus", "phone"),
]

# ─── Google Pixel ───────────────────────────────────────────────────
PIXEL_PATTERNS = [
    (r"pixel[ -]?(\d+)[ -]?pro", "Google Pixel {} Pro", "phone"),
    (r"pixel[ -]?(\d+)[ -]?xl", "Google Pixel {} XL", "phone"),
    (r"pixel[ -]?(\d+)", "Google Pixel {}", "phone"),
    (r"pixel[ -]?(\d+)[ -]?a", "Google Pixel {}a", "phone"),
]

# ─── HP printers (model from mDNS/HTTP) ─────────────────────────────
HP_PRINTER_MODELS = [
    "HP LaserJet Pro M404", "HP LaserJet Pro M428", "HP LaserJet Pro M454",
    "HP LaserJet Pro M479", "HP LaserJet Pro M501", "HP LaserJet Pro M506",
    "HP LaserJet Pro MFP M428", "HP LaserJet Pro MFP M479",
    "HP OfficeJet Pro 6970", "HP OfficeJet Pro 6960", "HP OfficeJet Pro 7740",
    "HP OfficeJet 5255", "HP OfficeJet 3830", "HP OfficeJet 4650",
    "HP ENVY Photo 7155", "HP ENVY Photo 6255", "HP ENVY 5055",
    "HP DeskJet 2655", "HP DeskJet 3755", "HP DeskJet 4155",
    "HP Color LaserJet Pro M454", "HP Color LaserJet Pro M479",
    "HP Smart Tank 5101", "HP Smart Tank 7001",
]

# ─── Sony / LG / Vizio TVs ──────────────────────────────────────────
TV_BRANDS = [
    (r"^(sony|kdl|xbr)[-_ ]?(\w+)?", "Sony TV ({})", "tv"),
    (r"^(lg|oled|uhd)[-_ ]?(\w+)?", "LG TV ({})", "tv"),
    (r"^vizio[-_ ]?(\w+)?", "Vizio TV ({})", "tv"),
    (r"^tcl[-_ ]?(\w+)?", "TCL TV ({})", "tv"),
    (r"^hisense[-_ ]?(\w+)?", "Hisense TV ({})", "tv"),
    (r"^(samsung|ue|ua|un)[-_ ]?(\w+)?", "Samsung TV ({})", "tv"),
]

# ─── Network equipment ─────────────────────────────────────────────
NETWORK_DEVICES = [
    (r"^ubiquiti|^unifi|^usg|^uap", "Ubiquiti UniFi", "network"),
    (r"^eero", "Amazon eero", "router"),
    (r"^orbi|^netgear", "Netgear Orbi", "router"),
    (r"^rt-?(\d+)", "ASUS RT-{}", "router"),
    (r"^nas|^synology|^ds[0-9]+", "Synology NAS", "nas"),
    (r"^qnap", "QNAP NAS", "nas"),
]

# ─── Gaming consoles ───────────────────────────────────────────────
GAMING = [
    (r"^ps[0-9]+|^playstation", "PlayStation", "console"),
    (r"^xbox", "Xbox", "console"),
    (r"^switch|^3ds|^new[ -]?3ds", "Nintendo Switch", "console"),
]

# ─── Smart speakers / IoT ──────────────────────────────────────────
SMART_DEVICES = [
    (r"^echo|^alexa", "Amazon Echo", "speaker"),
    (r"^nest", "Google Nest", "smart"),
    (r"^ring", "Ring Camera", "camera"),
    (r"^sonos", "Sonos Speaker", "speaker"),
    (r"^roku", "Roku Streaming Device", "tv"),
    (r"^chromecast", "Google Chromecast", "tv"),
    (r"^firetv|^fire[ -]?stick", "Amazon Fire TV", "tv"),
    (r"^philips[ -]?hue|^hue[ -]?bridge", "Philips Hue Bridge", "smart"),
    (r"^ecobee", "ecobee Thermostat", "thermostat"),
    (r"^arlo", "Arlo Camera", "camera"),
    (r"^wyze", "Wyze Camera", "camera"),
    (r"^tesla", "Tesla Vehicle", "car"),
    (r"^roomba|^irobot", "iRobot Roomba", "vacuum"),
]


def detect_device(hostname: str = "", vendor: str = "", mdns_services: list = None, traffic_domains: list = None) -> dict:
    """Returns { type, model, icon, label, category, confidence }"""
    mdns_services = mdns_services or []
    traffic_domains = traffic_domains or []

    h = (hostname or "").lower().strip()
    v = (vendor or "").lower().strip()

    # 0. Quick hostname matches (most reliable from ARP table)
    if h in ("thermostat",):
        return _res("thermostat", "Thermostat", "🌡️", "thermostat")
    if h in ("watch",):
        return _res("watch", "Smartwatch", "⌚", "watch")
    if h in ("ipad",):
        return _res("tablet", "iPad", "📱", "tablet")
    if h in ("iphone",):
        return _res("phone", "iPhone", "📱", "phone")
    # Hostnames like "iphone-xxx", "iphonedsearturo"
    if h.startswith("iphone"):
        return _res("phone", "iPhone", "📱", "phone")
    if h.startswith("ipad"):
        return _res("tablet", "iPad", "📱", "tablet")
    # "pixel-8", "pixel-7-pro"
    if h.startswith("pixel"):
        m = re.search(r"pixel[ -]?(\d+)[ -]?(pro|a)?", h)
        if m:
            model = f"Google Pixel {m.group(1)}"
            if m.group(2): model += f" {m.group(2).upper()}"
            return _res("phone", model, "📱", "phone")
        return _res("phone", "Google Pixel", "📱", "phone")
    # "galaxy-a04e", "galaxy-s24-ultra"
    if h.startswith("galaxy"):
        for pat, tmpl, cat in SAMSUNG_GALAXY:
            m = re.search(pat, h, re.IGNORECASE)
            if m:
                model = tmpl.format(*[g for g in m.groups() if g])
                return _res(cat, model, _icon_for(cat), cat)
        return _res("phone", "Samsung Galaxy", "📱", "phone")
    # "s24-de-erasmo" (Samsung Galaxy S24)
    if re.match(r"^s\d+", h):
        m = re.match(r"^s(\d+)", h)
        if m:
            return _res("phone", f"Samsung Galaxy S{m.group(1)}", "📱", "phone")
    # "43hisenserokutv", "40tclrokutv" — TV brand + roku in hostname
    if "rokutv" in h or "roku-tv" in h:
        if "hisense" in h:
            return _res("tv", "Hisense Roku TV", "📺", "tv")
        if "tcl" in h:
            return _res("tv", "TCL Roku TV", "📺", "tv")
        return _res("tv", "Roku TV", "📺", "tv")
    # "firestick-xxx"
    if h.startswith("firestick") or h.startswith("fire-stick"):
        return _res("tv", "Amazon Fire TV", "📺", "tv")
    # "c120" — likely a Tapo camera
    if re.match(r"^c\d+$", h):
        return _res("camera", "Tapo Camera", "📷", "camera")

    # 1. Router / Gateway
    if any(k in h for k in ["router", "gateway", "mynetwork", "home"]) or v in ["tp-link", "netgear", "asus", "ubiquiti"]:
        if "mynetwork" in h or "gateway" in h:
            return _res("router", "WiFi Router", "🌐", "router")
        for pat, model, cat in NETWORK_DEVICES:
            if re.search(pat, h, re.IGNORECASE):
                m = re.search(pat, h, re.IGNORECASE)
                return _res(cat, model.format(*m.groups()) if m.groups() and "{}" in model else model, _icon_for(cat), cat)
        return _res("router", "Router", "🌐", "router")

    # 2. Apple devices — most reliable via hostname + mDNS
    if "iphone" in h or "ipad" in h or "macbook" in h or "imac" in h or "apple-tv" in h or "homepod" in h or v == "apple":
        # Try to find Apple model from hostname patterns
        m = re.search(r"(iphone|ipad|macbook|imac|apple-?tv|homepod)[\-_ ]?(\w+)?", h, re.IGNORECASE)
        if m:
            kind = m.group(1).lower()
            extra = m.group(2) or ""
            if "iphone" in kind:
                return _res_apple("iPhone", extra, "📱", "phone")
            elif "ipad" in kind:
                return _res_apple("iPad", extra, "📱", "tablet")
            elif "macbook" in kind:
                return _res_apple("MacBook", extra, "💻", "laptop")
            elif "imac" in kind:
                return _res_apple("iMac", extra, "💻", "desktop")
            elif "apple-tv" in kind or "appletv" in kind:
                return _res("tv", "Apple TV", "📺", "tv")
            elif "homepod" in kind:
                return _res("speaker", "Apple HomePod", "🔊", "speaker")

        # mDNS-based detection
        if "_airplay" in str(mdns_services) or "_raop" in str(mdns_services) or "_companion-link" in str(mdns_services):
            # Apple device — infer type from services
            if "_companion-link" in str(mdns_services):
                if "apple-tv" in h:
                    return _res("tv", "Apple TV", "📺", "tv")
                return _res("phone", "iPhone (via AirPlay)", "📱", "phone")
            return _res("device", "Apple Device", "🍎", "phone")

    # 3. Samsung Galaxy
    if "samsung" in v or "sm-" in h or "galaxy" in h:
        for pat, tmpl, cat in SAMSUNG_GALAXY:
            m = re.search(pat, h, re.IGNORECASE)
            if m:
                model = tmpl.format(*[g for g in m.groups() if g])
                return _res(cat, model, _icon_for(cat), cat)
        return _res("phone", "Samsung Galaxy", "📱", "phone")

    # 4. Google Pixel
    if "pixel" in h or "google" in v:
        for pat, tmpl, cat in PIXEL_PATTERNS:
            m = re.search(pat, h, re.IGNORECASE)
            if m:
                model = tmpl.format(*[g for g in m.groups() if g])
                return _res(cat, model, _icon_for(cat), cat)
        if "_googlecast" in str(mdns_services):
            return _res("tv", "Google Chromecast", "📺", "tv")

    # 5. Printers
    if any(s in str(mdns_services) for s in ["_printer", "_ipp", "_ipps", "_pdl", "_scanner"]):
        if "hp" in v or "hewlett" in v or "hp" in h:
            for model in HP_PRINTER_MODELS:
                if model.lower().replace(" ", "") in h.replace(" ", ""):
                    return _res("printer", model, "🖨️", "printer")
            return _res("printer", "HP Printer", "🖨️", "printer")
        if "epson" in v or "epson" in h:
            return _res("printer", "Epson Printer", "🖨️", "printer")
        if "brother" in v or "brother" in h:
            return _res("printer", "Brother Printer", "🖨️", "printer")
        if "canon" in v or "canon" in h:
            return _res("printer", "Canon Printer", "🖨️", "printer")
        return _res("printer", "Network Printer", "🖨️", "printer")
    # Brother printer from hostname
    if "brother" in h or "hl-l" in h or "mfc-" in h:
        return _res("printer", "Brother Printer", "🖨️", "printer")

    # 6. TVs (Sony, LG, Vizio, TCL, Hisense)
    for pat, tmpl, cat in TV_BRANDS:
        m = re.search(pat, h, re.IGNORECASE)
        if m:
            model = tmpl.format(*[g for g in m.groups() if g])
            return _res("tv", model, "📺", cat)

    # 7. Streaming devices
    for pat, model, cat in SMART_DEVICES:
        if re.search(pat, h, re.IGNORECASE):
            return _res(cat, model, _icon_for(cat), cat)
    # Chromecast via mDNS
    if "_googlecast" in str(mdns_services):
        return _res("tv", "Google Chromecast", "📺", "tv")

    # 8. Gaming consoles
    for pat, model, cat in GAMING:
        if re.search(pat, h, re.IGNORECASE):
            return _res("console", model, "🎮", cat)

    # 9. Network equipment
    for pat, model, cat in NETWORK_DEVICES:
        if re.search(pat, h, re.IGNORECASE):
            return _res(cat, model, _icon_for(cat), cat)

    # 10. Fallback by vendor
    if v:
        # Samsung with private MAC = phone
        if "samsung" in v:
            return _res("phone", "Samsung Phone", "📱", "phone")
        return _res("device", v.title(), _icon_for_vendor(v), "device")

    return _res("device", "Unknown Device", "📡", "device")


def _res(category, model, icon, type_):
    return {"type": type_, "model": model, "icon": icon, "label": model, "category": category}


def _res_apple(kind, extra, icon, type_):
    model = kind
    if extra:
        model = f"{kind} {extra.upper()}"
    return _res(type_, model, icon, type_)


def _icon_for(category: str) -> str:
    return {
        "phone": "📱", "tablet": "📱", "laptop": "💻", "desktop": "🖥️",
        "tv": "📺", "speaker": "🔊", "router": "🌐", "network": "🌐",
        "nas": "💾", "console": "🎮", "printer": "🖨️", "camera": "📷",
        "smart": "🏠", "thermostat": "🌡️", "car": "🚗", "vacuum": "🤖",
    }.get(category, "📡")


def _icon_for_vendor(vendor: str) -> str:
    v = vendor.lower()
    if "apple" in v: return "🍎"
    if "samsung" in v: return "📱"
    if "google" in v: return "📱"
    if "sony" in v: return "📺"
    if "lg" in v: return "📺"
    if "vizio" in v: return "📺"
    if "hp" in v or "hewlett" in v: return "🖨️"
    if "epson" in v: return "🖨️"
    if "brother" in v: return "🖨️"
    if "canon" in v: return "🖨️"
    if "raspberry" in v: return "🥧"
    if "cisco" in v or "ubiquiti" in v or "netgear" in v or "tp-link" in v or "asus" in v: return "🌐"
    if "docker" in v or "virtual" in v: return "🐳"
    if "vmware" in v: return "🖥️"
    return "📡"


if __name__ == "__main__":
    # Quick test
    tests = [
        ("iPhone", "", [], []),
        ("Galaxy-S24-Ultra", "Samsung", [], []),
        ("MacBook-Pro-de-Yunior", "Apple", [], []),
        ("HP-LaserJet-Pro-M404", "HP", ["_printer._tcp"], []),
        ("DESKTOP-ABC123", "", [], []),
        ("raspberrypi", "Raspberry Pi", [], []),
        ("roku-12345", "", [], []),
        ("192.168.2.1", "TP-Link", [], []),
    ]
    for h, v, mdns, doms in tests:
        r = detect_device(h, v, mdns, doms)
        print(f"  {h:30s} → {r['icon']} {r['model']} ({r['type']})")
