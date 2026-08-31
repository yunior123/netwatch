#!/bin/bash
# netwatch: start|stop|status — parser + device discovery + Next.js panel
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IFACE="${NETWATCH_IFACE:-en0}"
PANEL_PORT="${NETWATCH_PORT:-3000}"
DISCOVER_INTERVAL="${NETWATCH_DISCOVER_INTERVAL:-30}"
PCAP="$ROOT/data/capture.pcap"
mkdir -p "$ROOT/data"

start() {
  stop >/dev/null 2>&1

  # Start pcap parser
  nohup python3 "$ROOT/parser.py" "$IFACE" >>"$ROOT/data/parser.log" 2>&1 &
  echo $! > "$ROOT/data/parser.pid"
  echo "parser OK (pid $(cat "$ROOT/data/parser.pid"))"

  # Start device discovery
  NETWATCH_IFACE="$IFACE" NETWATCH_DISCOVER_INTERVAL="$DISCOVER_INTERVAL" \
    nohup python3 "$ROOT/discover.py" >>"$ROOT/data/discover.log" 2>&1 &
  echo $! > "$ROOT/data/discover.pid"
  echo "discover OK (pid $(cat "$ROOT/data/discover.pid"), interval ${DISCOVER_INTERVAL}s)"

  # Start packet capture (needs root)
  if [ "$(id -u)" = "0" ]; then
    : > "$PCAP"
    nohup /usr/sbin/tcpdump -i "$IFACE" -U -s 256 -w "$PCAP" \
      'udp port 53 or udp port 5353 or tcp dst port 443' >>"$ROOT/data/capture.log" 2>&1 &
    echo $! > "$ROOT/data/capture.pid"
    echo "capture OK ($IFACE, pid $(cat "$ROOT/data/capture.pid"))"
  else
    echo "capture pendiente: sudo $0 start"
    if [ -s "$PCAP" ]; then
      echo "demo: using existing capture ($PCAP, $(wc -c < "$PCAP") bytes)"
    else
      echo "demo: seed traffic with: python3 $ROOT/scripts/synth_pcap.py && sudo $0 start"
    fi
  fi

  # Build + start Next.js panel (if panel/ exists and has package.json)
  if [ -f "$ROOT/panel/package.json" ]; then
    if [ ! -d "$ROOT/panel/node_modules" ]; then
      echo "installing panel dependencies..."
      (cd "$ROOT/panel" && npm install --silent) >>"$ROOT/data/panel.log" 2>&1
    fi
    if [ ! -d "$ROOT/panel/.next" ]; then
      echo "building panel..."
      (cd "$ROOT/panel" && npx next build) >>"$ROOT/data/panel.log" 2>&1
    fi
    NETWATCH_DATA_DIR="$ROOT/data" \
      nohup npx next start "$ROOT/panel" -p "$PANEL_PORT" >>"$ROOT/data/panel.log" 2>&1 &
    echo $! > "$ROOT/data/panel.pid"
    echo "panel OK (pid $(cat "$ROOT/data/panel.pid"))"
  else
    # Fallback: start legacy Python server
    nohup python3 "$ROOT/server.py" >>"$ROOT/data/server.log" 2>&1 &
    echo $! > "$ROOT/data/server.pid"
    echo "legacy server OK (pid $(cat "$ROOT/data/server.pid"))"
  fi

  echo ""
  echo "panel: http://127.0.0.1:${PANEL_PORT}"
}

stop() {
  for n in parser discover server panel capture; do
    [ -f "$ROOT/data/$n.pid" ] && kill "$(cat "$ROOT/data/$n.pid")" 2>/dev/null && rm -f "$ROOT/data/$n.pid"
  done
}

case "${1:-start}" in
  start)  start ;;
  stop)   stop; echo "stopped" ;;
  status)
    for n in parser discover server panel capture; do
      if [ -f "$ROOT/data/$n.pid" ] && kill -0 "$(cat "$ROOT/data/$n.pid")" 2>/dev/null; then
        echo "$n: RUNNING ($(cat "$ROOT/data/$n.pid"))"
      else
        echo "$n: down"
      fi
    done
    [ -f "$PCAP" ] && ls -lh "$PCAP" | awk '{print "pcap: "$5}' ;;
  restart)
    stop
    sleep 1
    start
    ;;
esac
