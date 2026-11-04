/**
 * Pages Function that hands backend and media paths to the edge Worker over a
 * service binding, so the browser sees one same-origin pages.dev host and the
 * Worker needs no public route. Everything else is static assets.
 */

export interface PagesEnv {
  EDGE: Fetcher;
}

export const FORWARDED_PREFIXES: readonly string[] = ["/api/", "/trs/", "/simulation/", "/media/"];

export const isForwardedPath = (pathname: string): boolean =>
  FORWARDED_PREFIXES.some((prefix) => pathname.startsWith(prefix));

export const onRequest: PagesFunction<PagesEnv> = (context) => {
  const { pathname } = new URL(context.request.url);
  if (!isForwardedPath(pathname)) return context.next();
  return context.env.EDGE.fetch(context.request);
};
