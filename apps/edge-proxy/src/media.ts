export interface MediaEnv {
  MEDIA_BUCKET: R2Bucket;
}

export const MEDIA_PREFIX = "/media/";

const HTTP_OK = 200;
const HTTP_PARTIAL_CONTENT = 206;
const HTTP_NOT_FOUND = 404;
const HTTP_METHOD_NOT_ALLOWED = 405;
const CACHE_CONTROL = "public, max-age=3600";
const FALLBACK_CONTENT_TYPE = "application/octet-stream";
const SANDBOX_CSP = "default-src 'none'; sandbox";

// NOTE: media shares the app's origin, so an inline-rendered upload could run
// script as the app. Only passive image, audio and video types are served inline.
const INLINE_CONTENT_TYPES: ReadonlySet<string> = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/gif",
  "image/avif",
  "audio/mpeg",
  "audio/mp4",
  "audio/aac",
  "audio/wav",
  "audio/x-wav",
  "audio/wave",
  "audio/ogg",
  "audio/webm",
  "video/mp4",
  "video/webm",
]);

const notFound = (): Response => new Response("Not found", { status: HTTP_NOT_FOUND });

const isInlineSafe = (contentType: string | null): boolean => {
  const mediaType = (contentType ?? "").split(";")[0].trim().toLowerCase();
  return INLINE_CONTENT_TYPES.has(mediaType);
};

const applyContentSafety = (headers: Headers): void => {
  if (!isInlineSafe(headers.get("Content-Type"))) {
    headers.set("Content-Type", FALLBACK_CONTENT_TYPE);
    headers.set("Content-Disposition", "attachment");
  }
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Content-Security-Policy", SANDBOX_CSP);
};

const baseHeaders = (object: R2Object): Headers => {
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  applyContentSafety(headers);
  headers.set("ETag", object.httpEtag ?? `"${object.etag}"`);
  headers.set("Accept-Ranges", "bytes");
  headers.set("Cache-Control", CACHE_CONTROL);
  return headers;
};

const resolveRange = (object: R2ObjectBody): { offset: number; length: number } | null => {
  const range = object.range as { offset?: number; length?: number; suffix?: number } | undefined;
  if (!range) return null;
  if (range.suffix !== undefined) {
    return { offset: object.size - range.suffix, length: range.suffix };
  }
  const offset = range.offset ?? 0;
  return { offset, length: range.length ?? object.size - offset };
};

const respondWithBody = (object: R2ObjectBody): Response => {
  const headers = baseHeaders(object);
  const range = resolveRange(object);
  if (!range) {
    headers.set("Content-Length", String(object.size));
    return new Response(object.body, { status: HTTP_OK, headers });
  }
  const last = range.offset + range.length - 1;
  headers.set("Content-Range", `bytes ${range.offset}-${last}/${object.size}`);
  headers.set("Content-Length", String(range.length));
  return new Response(object.body, { status: HTTP_PARTIAL_CONTENT, headers });
};

const respondToHead = async (key: string, env: MediaEnv): Promise<Response> => {
  const object = await env.MEDIA_BUCKET.head(key);
  if (!object) return notFound();
  const headers = baseHeaders(object);
  headers.set("Content-Length", String(object.size));
  return new Response(null, { status: HTTP_OK, headers });
};

const parseKey = (request: Request): string | null => {
  const encoded = new URL(request.url).pathname.slice(MEDIA_PREFIX.length);
  try {
    return decodeURIComponent(encoded);
  } catch {
    return null;
  }
};

export async function serveMedia(request: Request, env: MediaEnv): Promise<Response> {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return new Response("Method not allowed", {
      status: HTTP_METHOD_NOT_ALLOWED,
      headers: { Allow: "GET, HEAD" },
    });
  }
  const key = parseKey(request);
  if (key === null || key === "") return notFound();
  if (request.method === "HEAD") return respondToHead(key, env);
  const object = await env.MEDIA_BUCKET.get(key, { range: request.headers });
  return object ? respondWithBody(object) : notFound();
}
