import { describe, expect, it, vi } from "vitest";
import { isForwardedPath, onRequest, type PagesEnv } from "./_middleware";

const makeContext = (path: string, edgeResponse = new Response("from edge")) => {
  const edgeFetch = vi.fn().mockResolvedValue(edgeResponse);
  const next = vi.fn().mockResolvedValue(new Response("asset"));
  const request = new Request(`https://demo.pages.dev${path}`);
  const context = { request, env: { EDGE: { fetch: edgeFetch } } as unknown as PagesEnv, next };
  return { context, edgeFetch, next, request };
};

describe("isForwardedPath", () => {
  it("matches the four proxied prefixes only", () => {
    expect(isForwardedPath("/api/v1/x")).toBe(true);
    expect(isForwardedPath("/trs/v1/x")).toBe(true);
    expect(isForwardedPath("/simulation/v1/x")).toBe(true);
    expect(isForwardedPath("/media/a.png")).toBe(true);
    expect(isForwardedPath("/apix/v1")).toBe(false);
    expect(isForwardedPath("/discover")).toBe(false);
  });
});

describe("onRequest", () => {
  it("passes the untouched request to the edge Worker", async () => {
    const { context, edgeFetch, next, request } = makeContext("/api/v1/scenarios");

    const response = await onRequest(context as never);

    expect(edgeFetch).toHaveBeenCalledWith(request);
    expect(next).not.toHaveBeenCalled();
    expect(await response.text()).toBe("from edge");
  });

  it("serves static assets for every other path", async () => {
    const { context, edgeFetch, next } = makeContext("/assets/app.js");

    const response = await onRequest(context as never);

    expect(edgeFetch).not.toHaveBeenCalled();
    expect(next).toHaveBeenCalled();
    expect(await response.text()).toBe("asset");
  });
});
