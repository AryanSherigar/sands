/**
 * Cloudflare Worker in front of the Cloud Run backends.
 *
 * Replaces apps/frontend/nginx.conf.template in production: it forwards /api,
 * /trs and /simulation, stamps the shared proxy token the backends require, and replaces
 * X-Forwarded-For with the real client address so rate limiting keys on the
 * right IP. It also serves /media from the R2 bucket binding, so media needs no
 * public bucket URL. Pages serves everything else. It also triggers the memory outbox
 * relay on a cron.
 */

import { MEDIA_PREFIX, serveMedia, type MediaEnv } from "./media";

export interface Env extends MediaEnv {
  CORE_API_ORIGIN: string;
  TRS_ORIGIN: string;
  SIMULATION_ORIGIN: string;
  INTERNAL_PROXY_TOKEN: string;
  INTERNAL_SERVICE_TOKEN: string;
}

type OriginKey = "CORE_API_ORIGIN" | "TRS_ORIGIN" | "SIMULATION_ORIGIN";

const ROUTES: ReadonlyArray<{ prefix: string; origin: OriginKey }> = [
  { prefix: "/api/", origin: "CORE_API_ORIGIN" },
  { prefix: "/trs/", origin: "TRS_ORIGIN" },
  { prefix: "/simulation/", origin: "SIMULATION_ORIGIN" },
];

const HEADER_FORWARDED_FOR = "X-Forwarded-For";
const HEADER_FORWARDED_PROTO = "X-Forwarded-Proto";
const HEADER_PROXY_TOKEN = "X-Internal-Proxy-Token";
const HEADER_SERVICE_TOKEN = "X-Internal-Service-Token";
const HEADER_CLIENT_IP = "CF-Connecting-IP";
const RELAY_PATH = "/internal/memory/relay";
const HTTP_NOT_FOUND = 404;
const HTTP_BAD_GATEWAY = 502;

type StreamingRequestInit = RequestInit & { duplex: "half" };

const findRoute = (pathname: string) =>
  ROUTES.find((route) => pathname.startsWith(route.prefix) && pathname.length > route.prefix.length);

const upstreamHeaders = (request: Request, env: Env): Headers => {
  const headers = new Headers(request.headers);
  headers.delete("Host");
  headers.delete(HEADER_FORWARDED_FOR);
  const clientIp = request.headers.get(HEADER_CLIENT_IP);
  if (clientIp) headers.set(HEADER_FORWARDED_FOR, clientIp);
  headers.set(HEADER_FORWARDED_PROTO, "https");
  headers.set(HEADER_PROXY_TOKEN, env.INTERNAL_PROXY_TOKEN);
  return headers;
};

/** The request to send to a backend, or null when the path is not ours. */
export function buildUpstreamRequest(request: Request, env: Env): Request | null {
  const url = new URL(request.url);
  const route = findRoute(url.pathname);
  if (!route) return null;
  const target = `${env[route.origin]}/${url.pathname.slice(route.prefix.length)}${url.search}`;
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const init: StreamingRequestInit = {
    method: request.method,
    headers: upstreamHeaders(request, env),
    body: hasBody ? request.body : null,
    redirect: "manual",
    duplex: "half",
  };
  return new Request(target, init);
}

export async function runMemoryRelay(
  env: Env,
  fetchImpl: typeof fetch = fetch,
): Promise<void> {
  const request = new Request(`${env.TRS_ORIGIN}${RELAY_PATH}`, {
    method: "POST",
    headers: { [HEADER_SERVICE_TOKEN]: env.INTERNAL_SERVICE_TOKEN },
  });
  const response = await fetchImpl(request);
  if (!response.ok) {
    throw new Error(`memory relay failed with status ${response.status}`);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (new URL(request.url).pathname.startsWith(MEDIA_PREFIX)) {
      return serveMedia(request, env);
    }
    const upstream = buildUpstreamRequest(request, env);
    if (!upstream) return new Response("Not found", { status: HTTP_NOT_FOUND });
    try {
      return await fetch(upstream);
    } catch {
      return new Response("Bad gateway", { status: HTTP_BAD_GATEWAY });
    }
  },

  async scheduled(_controller: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(runMemoryRelay(env));
  },
} satisfies ExportedHandler<Env>;
