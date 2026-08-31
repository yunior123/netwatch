#!/bin/bash
# netwatch live capture — runs tcpdump writing to capture.pcap
# that parser.py tails for live traffic analysis.
# Usage: sudo ./live_capture.sh [interface]
set -e

IFACE="${1:-en0}"
DATA_DIR="$(dirname "$0")/data"
PCAP="$DATA_DIR/capture.pcap"

mkdir -p "$DATA_DIR"

# Remove old pcap so parser starts fresh
rm -f "$PCAP"

echo "netwatch: starting live capture on $IFACE → $PCAP"
echo "netwatch: parser.py will tail this file automatically"

# -U = packet-buffered output (writes after each packet)
# -s 128 = snaplen 128 bytes (enough for DNS/TLS headers)
# -n = don't resolve hostnames (faster)
exec tcpdump -i "$IFACE" -U -s 128 -n -w "$PCAP" 'port 53 or port 443 or port 5353 or port 67 or port 68'
