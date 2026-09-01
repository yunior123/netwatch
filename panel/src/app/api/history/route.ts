import { NextResponse } from "next/server";
import { readFile, stat } from "fs/promises";
import { join } from "path";

const DATA_DIR = join(process.cwd(), "..", "data");
const DB_PATH = join(DATA_DIR, "netwatch.db");

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const days = parseInt(searchParams.get("days") || "1");
    const dev = searchParams.get("device") || undefined;
    const host = searchParams.get("host") || undefined;
    const kind = searchParams.get("kind") || undefined;
    const service = searchParams.get("service") || undefined;
    const limit = parseInt(searchParams.get("limit") || "200");

    // Check if DB exists
    try {
      await stat(DB_PATH);
    } catch {
      return NextResponse.json({ events: [], total: 0, error: "No database" });
    }

    // Use Python to query SQLite (since Next.js doesn't have native SQLite)
    const { execSync } = await import("child_process");
    const since = Math.floor(Date.now() / 1000) - (days * 86400);
    
    let query = `SELECT * FROM events WHERE ts >= ${since}`;
    if (dev) query += ` AND dev = '${dev}'`;
    if (host) query += ` AND host LIKE '%${host}%'`;
    if (kind) query += ` AND kind = '${kind}'`;
    if (service) query += ` AND service = '${service}'`;
    query += ` ORDER BY ts DESC LIMIT ${limit}`;

    const cmd = `python3 -c "
import sqlite3, json
conn = sqlite3.connect('${DB_PATH}')
conn.row_factory = sqlite3.Row
rows = conn.execute('${query}').fetchall()
print(json.dumps([dict(r) for r in rows]))
"`;

    const result = execSync(cmd, { encoding: "utf-8", timeout: 5000 });
    const events = JSON.parse(result);

    // Get total count
    let countQuery = `SELECT COUNT(*) FROM events WHERE ts >= ${since}`;
    if (dev) countQuery += ` AND dev = '${dev}'`;
    if (host) countQuery += ` AND host LIKE '%${host}%'`;
    if (kind) countQuery += ` AND kind = '${kind}'`;
    if (service) countQuery += ` AND service = '${service}'`;

    const countResult = execSync(
      `python3 -c "
import sqlite3
conn = sqlite3.connect('${DB_PATH}')
print(conn.execute('${countQuery}').fetchone()[0])
"`,
      { encoding: "utf-8", timeout: 5000 }
    );

    return NextResponse.json({
      events,
      total: parseInt(countResult.trim()),
      days,
    });
  } catch (error) {
    return NextResponse.json(
      { events: [], total: 0, error: String(error) },
      { status: 500 }
    );
  }
}
