#!/bin/bash
# netwatch_start.sh — starts all netwatch services
# Live capture needs sudo (osascript will prompt for password once)
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="$DIR/data"
PCAP="$DATA/capture.pcap"

mkdir -p "$DATA"

# Kill any existing processes
pkill -f "parser.py" 2>/dev/null || true
pkill -f "discover.py" 2>/dev/null || true
pkill -f "tcpdump.*capture.pcap" 2>/dev/null || true
sleep 0.5

# Start tcpdump with osascript sudo prompt
rm -f "$PCAP"
osascript -e "do shell script \"tcpdump -i en0 -U -s 128 -n -w '$PCAP' 'port 53 or port 443 or port 5353 or port 67 or port 68'\" with administrator privileges" &
echo "netwatch: tcpdump started (sudo may have prompted)"
sleep 2

# Start parser (tails the pcap)
python3 "$DIR/parser.py" en0 &
echo "netwatch: parser started (PID $!)"

# Start device discovery
python3 "$DIR/discover.py" &
echo "netwatch: discover started (PID $!)"

# Start Next.js panel
cd "$DIR/panel"
npx next dev --port 3000 &
echo "netwatch: panel started on http://localhost:3000"

echo ""
echo "All netwatch services running. Press Ctrl+C to stop."
wait
