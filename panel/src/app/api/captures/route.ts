import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import { writeFile, readdir, stat, mkdir } from "fs/promises";
import { join, extname } from "path";

const execFileAsync = promisify(execFile);
const DATA_DIR = process.env.NETWATCH_DATA_DIR || join(process.cwd(), "..", "data");
const CAPTURES_DIR = join(DATA_DIR, "captures");
const TSHARK = process.env.PANEL_TSHARK || "tshark";

const ALLOWED_EXTS = new Set([".pcap", ".pcapng", ".cap"]);

async function listCaptures() {
  try {
    await mkdir(CAPTURES_DIR, { recursive: true });
    const files = await readdir(CAPTURES_DIR);
    const captures = [];
    for (const f of files) {
      if (!ALLOWED_EXTS.has(extname(f).toLowerCase())) continue;
      const st = await stat(join(CAPTURES_DIR, f));
      captures.push({ name: f, size: st.size, mtime: Math.floor(st.mtimeMs / 1000) });
    }
    return captures.sort((a, b) => b.mtime - a.mtime);
  } catch {
    return [];
  }
}

export async function GET() {
  const captures = await listCaptures();
  return NextResponse.json({ captures });
}

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const file = formData.get("file") as File | null;

  if (!file) {
    return NextResponse.json({ error: "no file uploaded" }, { status: 400 });
  }

  const ext = extname(file.name).toLowerCase();
  if (!ALLOWED_EXTS.has(ext)) {
    return NextResponse.json({ error: "only .pcap, .pcapng, .cap allowed" }, { status: 400 });
  }

  // Sanitize filename
  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");

  await mkdir(CAPTURES_DIR, { recursive: true });
  const buf = Buffer.from(await file.arrayBuffer());
  await writeFile(join(CAPTURES_DIR, safeName), buf);

  // Run tshark to get summary stats
  let stats: Record<string, unknown> = { name: safeName, size: buf.length };
  try {
    const { stdout } = await execFileAsync(TSHARK, [
      "-r", join(CAPTURES_DIR, safeName),
      "-q",
      "-z", "io,stat,0",
      "-z", "wlan,stat",
    ], { timeout: 15000 });
    stats.summary = stdout;
  } catch {
    // Stats are optional
  }

  return NextResponse.json(stats);
}
