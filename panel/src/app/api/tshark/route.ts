import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import { existsSync } from "fs";
import { join } from "path";

const execFileAsync = promisify(execFile);
const DATA_DIR = process.env.NETWATCH_DATA_DIR || join(process.cwd(), "..", "data");
const TSHARK = process.env.PANEL_TSHARK || "tshark";

const CURATED_FILTERS = [
  { key: "all", label: "All Wi-Fi frames", filter: "wlan", description: "Every 802.11 frame in the capture" },
  { key: "beacons", label: "Beacon frames (0x08)", filter: "wlan.fc.type_subtype == 0x08", description: "AP advertising its SSID, channel, capabilities" },
  { key: "probes_req", label: "Probe requests (0x04)", filter: "wlan.fc.type_subtype == 0x04", description: "Clients actively searching for a network" },
  { key: "probes_resp", label: "Probe responses (0x05)", filter: "wlan.fc.type_subtype == 0x05", description: "AP answering a probe request" },
  { key: "deauth", label: "Deauthentication (0x0c)", filter: "wlan.fc.type_subtype == 0x0c", description: "Disassociation events, including rogue deauth attacks" },
  { key: "disassoc", label: "Disassociation (0x0a)", filter: "wlan.fc.type_subtype == 0x0a", description: "Graceful tear-down between client and AP" },
  { key: "auth", label: "Authentication (0x0b)", filter: "wlan.fc.type_subtype == 0x0b", description: "Open/shared-key authentication exchanges" },
  { key: "assoc_req", label: "Association request (0x00)", filter: "wlan.fc.type_subtype == 0x00", description: "Client asks to join an AP" },
  { key: "assoc_resp", label: "Association response (0x01)", filter: "wlan.fc.type_subtype == 0x01", description: "AP accepts/rejects a client" },
  { key: "eapol", label: "EAPOL (4-way handshake)", filter: "eapol", description: "WPA-PBKDF2 key handshake" },
  { key: "data", label: "Data frames", filter: "wlan.fc.type == 0x02", description: "All actual traffic frames" },
  { key: "data_protected", label: "Encrypted data frames", filter: "wlan.fc.type == 0x02 and wlan.fc.protected == 1", description: "Data frames with the Protected bit set" },
  { key: "retries", label: "Retried frames", filter: "wlan.fc.retry == 1", description: "Retransmissions, useful to spot noisy clients" },
  { key: "broadcast_mgmt", label: "Broadcast/multicast mgmt", filter: "wlan.fc.type == 0x00 and (wlan.ff_bc_multicast)", description: "Management traffic sent to everyone" },
  { key: "dns", label: "DNS traffic", filter: "dns", description: "All DNS queries and responses" },
  { key: "tls", label: "TLS traffic", filter: "tls", description: "TLS handshake and application data" },
  { key: "http", label: "HTTP traffic", filter: "http", description: "Plain HTTP requests and responses" },
  { key: "arp", label: "ARP traffic", filter: "arp", description: "Address Resolution Protocol" },
];

const DEFAULT_FIELDS = [
  "frame.number",
  "frame.time_epoch",
  "wlan.fc.type_subtype",
  "wlan.sa",
  "wlan.da",
  "wlan.bssid",
  "wlan.ssid",
  "_ws.col.Info",
];

export async function GET() {
  return NextResponse.json({ filters: CURATED_FILTERS });
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { capture, display_filter, max_rows = 500, fields } = body;

  if (!capture) {
    return NextResponse.json({ error: "capture name required" }, { status: 400 });
  }

  // Security: confine to data dir
  const capturePath = join(DATA_DIR, capture);
  if (!existsSync(capturePath)) {
    return NextResponse.json({ error: "capture not found" }, { status: 404 });
  }

  const useFields = fields || DEFAULT_FIELDS;
  const filter = display_filter || "wlan";

  const args = [
    "-r", capturePath,
    "-n",
    "-Y", filter,
    "-T", "fields",
    "-E", "separator=/t",
    "-E", "occurrence=f",
    "-c", String(max_rows),
    ...useFields.flatMap((f: string) => ["-e", f]),
  ];

  try {
    const { stdout, stderr } = await execFileAsync(TSHARK, args, {
      timeout: 30000,
      maxBuffer: 10 * 1024 * 1024,
    });

    const rows = stdout
      .split("\n")
      .filter((line) => line.trim())
      .map((line) => {
        const cols = line.split("\t");
        const row: Record<string, string> = {};
        useFields.forEach((f: string, i: number) => {
          row[f] = cols[i] || "";
        });
        return row;
      });

    return NextResponse.json({
      capture,
      filter,
      fields: useFields,
      rows,
      truncated: rows.length >= max_rows,
      error: stderr.trim() || null,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "tshark failed";
    return NextResponse.json({
      capture,
      filter,
      fields: useFields,
      rows: [],
      truncated: false,
      error: msg,
    });
  }
}
