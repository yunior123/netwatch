// SSE endpoint — watches state.json/devices.json and pushes changes to clients
import { readFile } from "fs/promises";
import { watch } from "fs";
import { join } from "path";

const DATA_DIR = join(process.cwd(), "..", "data");
const clients = new Set<ReadableStreamDefaultController>();

function startWatching() {
  try {
    watch(join(DATA_DIR, "state.json"), () => pushState());
  } catch {
    setInterval(() => pushState(), 1000);
  }
  try {
    watch(join(DATA_DIR, "devices.json"), () => pushState());
  } catch {}
}

async function pushState() {
  if (clients.size === 0) return;
  try {
    const raw = await readFile(join(DATA_DIR, "state.json"), "utf-8");
    const state = JSON.parse(raw);
    const devsRaw = await readFile(join(DATA_DIR, "devices.json"), "utf-8");
    const devs = JSON.parse(devsRaw);

    const msg = `data: ${JSON.stringify({
      type: "state",
      packets: state.packets,
      events: state.events || [],
      domains: state.domains || {},
      devices: devs.devices || {},
      updated: state.updated,
      iface: state.iface,
    })}\n\n`;

    for (const client of clients) {
      try {
        client.enqueue(msg);
      } catch {
        clients.delete(client);
      }
    }
  } catch {}
}

export async function GET(req: Request) {
  if (clients.size === 0) startWatching();

  const stream = new ReadableStream({
    start(controller) {
      clients.add(controller);
      controller.enqueue(`data: ${JSON.stringify({ type: "connected" })}\n\n`);
      pushState();
      (req as { signal?: AbortSignal }).signal?.addEventListener("abort", () => {
        clients.delete(controller);
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
