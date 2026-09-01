import { NextResponse } from "next/server";
import { execSync } from "child_process";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const key = execSync(
      `security find-generic-password -a "$USER" -s "nvidia-nim-api-key" -w 2>/dev/null`,
      { encoding: "utf-8", timeout: 5000 }
    ).trim();

    if (!key) {
      return NextResponse.json({ models: [], error: "No NIM API key in keychain" });
    }

    const result = execSync(
      `curl -s "https://integrate.api.nvidia.com/v1/models" -H "Authorization: Bearer ${key}"`,
      { encoding: "utf-8", timeout: 15000 }
    );

    const data = JSON.parse(result);
    const models = (data.data || []).map((m: { id: string }) => m.id).sort();

    return NextResponse.json({ models });
  } catch (error) {
    return NextResponse.json({ models: [], error: String(error) });
  }
}
