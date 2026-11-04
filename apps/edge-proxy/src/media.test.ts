import { beforeEach, describe, expect, it } from "vitest";
import { serveMedia, type MediaEnv } from "./media";

const BODY = "0123456789";

interface FakeObject {
  size: number;
  etag: string;
  range?: { offset: number; length: number };
  body: ReadableStream | null;
  writeHttpMetadata: (headers: Headers) => void;
}

let storedContentType = "audio/mpeg";

const makeObject = (range?: { offset: number; length: number }): FakeObject => {
  const text = range ? BODY.slice(range.offset, range.offset + range.length) : BODY;
  return {
    size: BODY.length,
    etag: "abc",
    range,
    body: new Response(text).body,
    writeHttpMetadata: (headers) => headers.set("Content-Type", storedContentType),
  };
};

const makeEnv = (stored: Record<string, boolean>): MediaEnv => ({
  MEDIA_BUCKET: {
    get: async (key: string, options?: { range?: Headers }) => {
      if (!stored[key]) return null;
      return makeObject(options?.range?.get("Range") ? { offset: 2, length: 4 } : undefined);
    },
    head: async (key: string) => (stored[key] ? { ...makeObject(), body: null } : null),
  } as unknown as MediaEnv["MEDIA_BUCKET"],
});

const request = (path: string, init: RequestInit = {}): Request =>
  new Request(`https://app.example.test${path}`, init);

describe("serveMedia", () => {
  beforeEach(() => {
    storedContentType = "audio/mpeg";
  });

  it("serves an object with its stored content type", async () => {
    const response = await serveMedia(request("/media/covers/a.mp3"), makeEnv({ "covers/a.mp3": true }));

    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("audio/mpeg");
    expect(response.headers.get("Accept-Ranges")).toBe("bytes");
    expect(await response.text()).toBe(BODY);
  });

  it("answers 404 for a missing object and for an empty key", async () => {
    const env = makeEnv({});

    expect((await serveMedia(request("/media/nope.png"), env)).status).toBe(404);
    expect((await serveMedia(request("/media/"), env)).status).toBe(404);
    expect((await serveMedia(request("/media/%E0%A4%A"), env)).status).toBe(404);
  });

  it("answers a Range request with 206 and a Content-Range", async () => {
    const response = await serveMedia(
      request("/media/a.mp3", { headers: { Range: "bytes=2-5" } }),
      makeEnv({ "a.mp3": true }),
    );

    expect(response.status).toBe(206);
    expect(response.headers.get("Content-Range")).toBe("bytes 2-5/10");
    expect(await response.text()).toBe("2345");
  });

  it("answers HEAD without a body", async () => {
    const response = await serveMedia(request("/media/a.mp3", { method: "HEAD" }), makeEnv({ "a.mp3": true }));

    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Length")).toBe("10");
    expect(await response.text()).toBe("");
  });

  it("rejects writes", async () => {
    const response = await serveMedia(request("/media/a.mp3", { method: "PUT", body: "x" }), makeEnv({ "a.mp3": true }));

    expect(response.status).toBe(405);
    expect(response.headers.get("Allow")).toBe("GET, HEAD");
  });

  it("marks every response nosniff and sandboxed", async () => {
    const response = await serveMedia(request("/media/a.mp3"), makeEnv({ "a.mp3": true }));

    expect(response.headers.get("X-Content-Type-Options")).toBe("nosniff");
    expect(response.headers.get("Content-Security-Policy")).toBe("default-src 'none'; sandbox");
  });

  it.each(["text/html", "image/svg+xml", "application/xhtml+xml", "text/javascript"])(
    "never serves %s inline",
    async (contentType) => {
      storedContentType = contentType;

      const response = await serveMedia(request("/media/a"), makeEnv({ a: true }));

      expect(response.headers.get("Content-Type")).toBe("application/octet-stream");
      expect(response.headers.get("Content-Disposition")).toBe("attachment");
    },
  );

  it("keeps safe media types inline, ignoring content-type parameters", async () => {
    storedContentType = "image/png; charset=binary";

    const response = await serveMedia(request("/media/a.png"), makeEnv({ "a.png": true }));

    expect(response.headers.get("Content-Type")).toBe("image/png; charset=binary");
    expect(response.headers.get("Content-Disposition")).toBeNull();
  });

  it("keeps the x-wav type the backends write inline", async () => {
    storedContentType = "audio/x-wav";

    const response = await serveMedia(request("/media/a.wav"), makeEnv({ "a.wav": true }));

    expect(response.headers.get("Content-Type")).toBe("audio/x-wav");
    expect(response.headers.get("Content-Disposition")).toBeNull();
  });

  it("treats an object with no content type as a download", async () => {
    storedContentType = "";

    const response = await serveMedia(request("/media/a"), makeEnv({ a: true }));

    expect(response.headers.get("Content-Disposition")).toBe("attachment");
  });
});
