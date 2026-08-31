"""OUI vendor lookup — maps MAC address prefixes to manufacturer names.
Lightweight, no external DB needed. Covers top 200 most common vendors."""
import re

OUI_DB: dict[str, str] = {
    # Apple
    "A4:83:E7": "Apple", "F0:18:98": "Apple", "AC:BC:32": "Apple",
    "3C:22:FB": "Apple", "A8:5C:2C": "Apple", "C8:69:CD": "Apple",
    "DC:A4:CA": "Apple", "F8:FF:C2": "Apple", "20:EE:28": "Apple",
    "14:7D:DA": "Apple", "6C:96:CF": "Apple", "B0:BE:76": "Apple",
    "38:F9:D7": "Apple", "8C:85:90": "Apple", "A0:99:9B": "Apple",
    "0C:30:21": "Apple", "78:7B:8A": "Apple", "AC:DE:48": "Apple",
    "5C:AD:BA": "Apple",  # Apple private WiFi address
    # Samsung
    "3E:61:2D": "Samsung", "7A:D8:98": "Samsung", "8A:6D:1C": "Samsung",
    "BE:38:17": "Samsung", "22:03:8E": "Samsung", "00:1E:58": "Samsung",
    "00:1A:8A": "Samsung", "34:C3:AC": "Samsung", "F8:04:2E": "Samsung",
    "E4:7C:F9": "Samsung", "B4:3A:28": "Samsung", "24:4B:81": "Samsung",
    # Google/Pixel
    "3C:5A:B4": "Google", "F4:F5:E8": "Google", "20:DF:B9": "Google",
    "6C:AE:43": "Google", "A4:60:32": "Google", "DC:A6:32": "Google",
    # Intel
    "00:1B:21": "Intel", "3C:97:0E": "Intel", "AC:67:5D": "Intel",
    "F8:63:3F": "Intel", "48:51:B7": "Intel", "8C:8D:28": "Intel",
    # Cisco
    "00:1A:A1": "Cisco", "00:26:0B": "Cisco", "C8:00:84": "Cisco",
    "5C:50:15": "Cisco", "B0:AA:77": "Cisco", "EC:FA:BC": "Cisco",
    # TP-Link
    "50:C7:BF": "TP-Link", "14:CF:92": "TP-Link", "60:32:B1": "TP-Link",
    "C0:06:C3": "TP-Link", "B0:95:75": "TP-Link", "D8:07:B6": "TP-Link",
    # Netgear
    "C0:3F:0E": "Netgear", "44:94:FC": "Netgear", "A4:2B:8C": "Netgear",
    "B0:B9:8A": "Netgear", "20:E5:2A": "Netgear",
    # ASUS
    "04:D4:C4": "ASUS", "1C:87:2C": "ASUS", "2C:56:DC": "ASUS",
    "40:16:7E": "ASUS", "60:45:CB": "ASUS", "AC:9E:17": "ASUS",
    # Dell
    "00:14:22": "Dell", "18:A9:05": "Dell", "34:17:EB": "Dell",
    "B0:83:FE": "Dell", "D4:AE:52": "Dell", "F8:BC:12": "Dell",
    # HP
    "00:1B:78": "HP", "00:23:7D": "HP", "10:1F:74": "HP",
    "28:92:4A": "HP", "3C:D9:2B": "HP", "64:51:06": "HP",
    # Lenovo
    "3C:97:0E": "Lenovo", "50:5B:C2": "Lenovo", "70:5A:0F": "Lenovo",
    "8C:EC:4B": "Lenovo", "C8:5B:76": "Lenovo", "E8:2A:44": "Lenovo",
    # Microsoft/Xbox
    "7C:1E:52": "Microsoft", "B8:31:B5": "Microsoft", "28:18:78": "Microsoft",
    "60:45:BD": "Microsoft", "CC:3B:08": "Microsoft",
    # Sony
    "00:04:1F": "Sony", "20:89:84": "Sony", "3C:5A:B4": "Sony",
    "5C:B0:67": "Sony", "84:78:AC": "Sony", "F0:BF:97": "Sony",
    # LG
    "00:1C:62": "LG", "10:68:3F": "LG", "2C:54:CF": "LG",
    "30:76:6F": "LG", "50:55:3A": "LG", "88:C9:D0": "LG",
    # Huawei
    "00:E0:FC": "Huawei", "20:08:ED": "Huawei", "48:46:FB": "Huawei",
    "70:72:3C": "Huawei", "88:CF:98": "Huawei", "CC:53:B5": "Huawei",
    # Xiaomi
    "28:6C:07": "Xiaomi", "64:B4:73": "Xiaomi", "78:11:DC": "Xiaomi",
    "A4:08:EA": "Xiaomi", "C4:6A:B7": "Xiaomi", "F0:B4:29": "Xiaomi",
    # Roku
    "B0:A7:37": "Roku", "CC:5A:9F": "Roku", "8C:3A:E3": "Roku",
    "DC:3A:5E": "Roku", "E0:6C:79": "Roku",
    # Sonos
    "B8:E9:37": "Sonos", "48:0D:34": "Sonos", "5C:AA:FD": "Sonos",
    "94:43:C7": "Sonos", "D0:54:2B": "Sonos",
    # Ring/Nest
    "4C:6F:37": "Ring", "8C:3F:AA": "Ring", "28:6C:37": "Nest",
    # Ubiquiti
    "04:18:D6": "Ubiquiti", "18:E8:29": "Ubiquiti", "24:5A:4C": "Ubiquiti",
    "44:D9:E7": "Ubiquiti", "74:83:C2": "Ubiquiti", "B4:FB:E4": "Ubiquiti",
    # Synology/QNAP
    "00:11:32": "Synology", "24:5E:BE": "QNAP", "00:08:2F": "QNAP",
    # Printer brands
    "00:1B:A8": "Brother", "00:1E:8F": "Epson", "00:26:AB": "Canon",
    "18:60:24": "HP-Print", "30:CD:A7": "HP-Print",
    "8C:8B:5B": "Brother",  # Brother printers
    "B0:68:E6": "Brother",  # Brother printers
    # IoT / Smart Home
    "B4:E6:2D": "Espressif", "EC:FA:BC": "Tuya", "18:B7:35": "Tuya",
    "50:02:91": "Raspberry-Pi", "28:CD:C1": "Raspberry-Pi",
    # Docker/VM
    "02:42:AC": "Docker", "02:42:0A": "Docker", "08:00:27": "VirtualBox",
}


def lookup_vendor(mac: str) -> str:
    """Look up vendor from MAC address prefix."""
    if not mac:
        return ""
    # Normalize
    mac = mac.upper().strip()
    # Try OUI (first 3 octets)
    prefix = mac[:8]
    if prefix in OUI_DB:
        return OUI_DB[prefix]
    # Try first 2 octets (less precise)
    prefix6 = mac[:5]
    for k, v in OUI_DB.items():
        if k.startswith(prefix6):
            return v
    return ""
