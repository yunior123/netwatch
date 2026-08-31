import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

const DATA_DIR = join(process.cwd(), "..", "data");

export async function GET() {
  try {
    const devicesPath = join(DATA_DIR, "devices.json");
    const raw = await readFile(devicesPath, "utf-8");
    const devices = JSON.parse(raw);
    return NextResponse.json(devices, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(
      { updated: 0, iface: "", count: 0, devices: {} },
      { headers: { "Cache-Control": "no-store" } }
    );
  }
}
