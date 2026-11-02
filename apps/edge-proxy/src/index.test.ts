import { describe, expect, it, vi } from "vitest";
import worker, { buildUpstreamRequest, runMemoryRelay, type Env } from "./index";

const ENV: Env = {
  CORE_API_ORIGIN: "https://core.example.run.app",
  TRS_ORIGIN: "https://trs.example.run.app",
  SIMULATION_ORIGIN: "https://simulation.example.run.app",
  INTERNAL_PROXY_TOKEN: "proxy-token",
  INTERNAL_SERVICE_TOKEN: "service-token",
};
const CLIENT_IP = "203.0.113.9";
const SPOOFED_IP = "10.9.9.9";

const incoming = (path: string, init: RequestInit = {}): Request =>
  new Request(`https://app.example.test${path}`, {
    ...init,
    headers: { "CF-Connecting-IP": CLIENT_IP, ...(init.headers ?? {}) },
  });

describe("buildUpstreamRequest routing", () => {
  it("sends /api/* to the core api with the prefix stripped", () => {
    const upstream = buildUpstreamRequest(incoming("/api/v1/scenarios?x=1"), ENV);

    expect(upstream?.url).toBe("https://core.example.run.app/v1/scenarios?x=1");
  });

  it("sends /trs/* to the turn service with the prefix stripped", () => {
    const upstream = buildUpstreamRequest(incoming("/trs/v1/turn"), ENV);

    expect(upstream?.url).toBe("https://trs.example.run.app/v1/turn");
  });

  it("sends /simulation/* to the simulation with the prefix stripped", () => {
    const upstream = buildUpstreamRequest(incoming("/simulation/v1/playthroughs/1/world"), ENV);

    expect(upstream?.url).toBe("https://simulation.example.run.app/v1/playthroughs/1/world");
  });

  it("returns null for paths the Worker does not own", () => {
    expect(buildUpstreamRequest(incoming("/"), ENV)).toBeNull();
    expect(buildUpstreamRequest(incoming("/assets/app.js"), ENV)).toBeNull();
    expect(buildUpstreamRequest(incoming("/apix/v1"), ENV)).toBeNull();
  });

  it("does not route the bare prefix without a trailing path", () => {
    expect(buildUpstreamRequest(incoming("/api"), ENV)).toBeNull();
  });
});

describe("buildUpstreamRequest headers", () => {
  it("overwrites a client-supplied X-Forwarded-For with the real client ip", () => {
    const upstream = buildUpstreamRequest(
      incoming("/api/v1/x", { headers: { "X-Forwarded-For": SPOOFED_IP } }),
      ENV,
    );

    expect(upstream?.headers.get("X-Forwarded-For")).toBe(CLIENT_IP);
  });

  it("drops X-Forwarded-For when Cloudflare gave no client ip", () => {
    const request = new Request("https://app.example.test/api/v1/x", {
      headers: { "X-Forwarded-For": SPOOFED_IP },
    });

    const upstream = buildUpstreamRequest(request, ENV);

    expect(upstream?.headers.has("X-Forwarded-For")).toBe(false);
  });

  it("replaces a client-supplied proxy token with the secret one", () => {
    const upstream = buildUpstreamRequest(
      incoming("/api/v1/x", { headers: { "X-Internal-Proxy-Token": "guess" } }),
      ENV,
    );

    expect(upstream?.headers.get("X-Internal-Proxy-Token")).toBe("proxy-token");
  });

  it("marks the request as https and keeps authorization and content type", () => {
    const upstream = buildUpstreamRequest(
      incoming("/trs/v1/turn", {
        method: "POST",
        body: "{}",
        headers: { Authorization: "Bearer abc", "Content-Type": "application/json" },
      }),
      ENV,
    );

    expect(upstream?.headers.get("X-Forwarded-Proto")).toBe("https");
    expect(upstream?.headers.get("Authorization")).toBe("Bearer abc");
    expect(upstream?.headers.get("Content-Type")).toBe("application/json");
  });

  it("keeps the method and forwards the body", async () => {
    const upstream = buildUpstreamRequest(
      incoming("/api/v1/x", { method: "POST", body: "payload" }),
      ENV,
    );

    expect(upstream?.method).toBe("POST");
    expect(await upstream?.text()).toBe("payload");
  });

  it("sends no body for a GET", () => {
    const upstream = buildUpstreamRequest(incoming("/api/v1/x"), ENV);

    expect(upstream?.body).toBeNull();
  });
});

describe("fetch handler", () => {
  it("returns the upstream response untouched, including a streamed body", async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode("event: narration\n\n"));
        controller.close();
      },
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(stream, { headers: { "Content-Type": "text/event-stream" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await worker.fetch(incoming("/trs/v1/turn", { method: "POST", body: "{}" }), ENV);

    expect(response.headers.get("Content-Type")).toBe("text/event-stream");
    expect(await response.text()).toBe("event: narration\n\n");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });

  it("answers 404 for paths it does not own, without calling a backend", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await worker.fetch(incoming("/somewhere"), ENV);

    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("answers 502 when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect failed")));

    const response = await worker.fetch(incoming("/api/v1/x"), ENV);

    expect(response.status).toBe(502);
    vi.unstubAllGlobals();
  });
});

describe("runMemoryRelay", () => {
  it("posts to the relay endpoint with only the service token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));

    await runMemoryRelay(ENV, fetchMock);

    const request: Request = fetchMock.mock.calls[0][0];
    expect(request.url).toBe("https://trs.example.run.app/internal/memory/relay");
    expect(request.method).toBe("POST");
    expect(request.headers.get("X-Internal-Service-Token")).toBe("service-token");
    expect(request.headers.has("X-Internal-Proxy-Token")).toBe(false);
  });

  it("throws when the relay answers an error so the cron run is marked failed", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("no", { status: 500 }));

    await expect(runMemoryRelay(ENV, fetchMock)).rejects.toThrow(/500/);
  });

  it("is run by the scheduled handler", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const waitUntil = vi.fn();

    await worker.scheduled({} as ScheduledController, ENV, { waitUntil } as unknown as ExecutionContext);
    await waitUntil.mock.calls[0][0];

    expect(fetchMock).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });
});
