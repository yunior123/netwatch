import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

const DATA_DIR = join(process.cwd(), "..", "data");

export async function GET() {
  try {
    const statePath = join(DATA_DIR, "state.json");
    const raw = await readFile(statePath, "utf-8");
    const state = JSON.parse(raw);
    return NextResponse.json(state, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(
      { empty: true, events: [], domains: {}, devices: {}, packets: 0 },
      { headers: { "Cache-Control": "no-store" } }
    );
  }
}
