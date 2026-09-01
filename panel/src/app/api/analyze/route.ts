import { NextResponse } from "next/server";
import { execSync } from "child_process";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { domain, model, device, events } = body;

    const selectedModel = model || "deepseek-ai/deepseek-v4-flash-0731";

    const key = execSync(
      `security find-generic-password -a "$USER" -s "nvidia-nim-api-key" -w 2>/dev/null`,
      { encoding: "utf-8", timeout: 5000 }
    ).trim();

    if (!key) {
      return NextResponse.json({ error: "No NIM API key in keychain. Run: security add-generic-password -a $USER -s nvidia-nim-api-key -w 'nvapi-YOUR_KEY'" });
    }

    let prompt = "";

    if (domain) {
      prompt = `Investigate this domain/URL for security threats: ${domain}

Report in this format:
- WHAT: What is this domain?
- THREATS: Any known malware, C2, phishing associations?
- RISK: LOW / MEDIUM / HIGH / CRITICAL
- ACTION: What should the user do?

Be concise. 2-3 sentences max.`;
    } else if (device) {
      const deviceName = device.device_model || device.hostname || device.ip;
      const services = Object.keys(device.services || {}).join(", ");
      const topDomains = Object.entries(device.domains || {})
        .sort((a, b) => (b[1] as number) - (a[1] as number))
        .slice(0, 10)
        .map(([d, c]) => `${d} (${c})`)
        .join(", ");

      prompt = `Analyze this device's network behavior for security concerns:

Device: ${deviceName} (${device.ip}) — ${device.vendor || "Unknown vendor"}
Services: ${services || "none detected"}
Top domains: ${topDomains || "none"}

Flag anything suspicious. Be concise. 3-4 sentences max.`;
    } else if (events && events.length > 0) {
      const eventLines = events.slice(-30).map((e: { t: number; dev: string; kind: string; host: string; service?: string }) => {
        const t = new Date(e.t * 1000).toTimeString().slice(0, 8);
        return `${t} ${e.dev} ${e.kind} ${e.host} ${e.service || ""}`;
      }).join("\n");

      prompt = `Analyze these network events for security threats:

${eventLines}

Flag anything suspicious: malicious domains, C2 beaconing, data exfiltration, unusual patterns. Be concise. 3-4 sentences max.`;
    } else {
      return NextResponse.json({ error: "Provide domain, device, or events" });
    }

    const payload = JSON.stringify({
      model: selectedModel,
      messages: [
        { role: "system", content: "You are a network security analyst. Be concise and direct. Flag real threats only." },
        { role: "user", content: prompt }
      ],
      temperature: 0.2,
      max_tokens: 500,
    });

    const result = execSync(
      `curl -s --max-time 120 "https://integrate.api.nvidia.com/v1/chat/completions" -H "Authorization: Bearer ${key}" -H "Content-Type: application/json" -d '${payload.replace(/'/g, "'\\''")}'`,
      { encoding: "utf-8", timeout: 130000 }
    );

    const resp = JSON.parse(result);
    const msg = resp.choices?.[0]?.message;
    const content = msg?.content || msg?.reasoning_content || "No response";

    return NextResponse.json({
      analysis: content,
      model: selectedModel,
      tokens: resp.usage || {},
    });
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
