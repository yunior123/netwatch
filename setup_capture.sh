#!/bin/bash
# netwatch: one-time setup for live packet capture
# Run with sudo ONCE: sudo ./setup_capture.sh
# After that, tcpdump runs automatically at boot (no sudo needed)
set -e

PLIST="$HOME/Library/LaunchAgents/com.netwatch.capture.plist"
LABEL="com.netwatch.capture"

# Ensure data dir exists
mkdir -p "$(dirname "$0")/data"

# Unload if already loaded
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
sleep 0.5

# Load the launchd job (runs tcpdump as root)
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "✓ Live capture started. tcpdump will now write to data/capture.pcap"
echo "✓ It will restart automatically on reboot."
echo ""
echo "Start the rest of netwatch:"
echo "  python3 parser.py en0 &"
echo "  python3 discover.py &"
echo "  cd panel && npx next dev --port 3000"
