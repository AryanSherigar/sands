export const ALPHA_EVENTS_ENDPOINT = "/v1/alpha/events";
export const ALPHA_EVENTS_FLUSH_INTERVAL_MS = 10_000;
export const ALPHA_EVENTS_MAX_BATCH = 50;
export const ALPHA_EVENTS_MAX_QUEUE = 200;
export const ALPHA_EVENTS_FAILURE_WARNING =
  "Alpha event delivery failed; events in that batch were dropped.";

export const VIEWPORT_PHONE_MAX_PX = 768;
export const VIEWPORT_TABLET_MAX_PX = 1024;
export const VIEWPORT_BUCKETS: ReadonlyArray<readonly [string, number]> = [
  ["xs", 480],
  ["sm", 768],
  ["md", 1024],
  ["lg", 1440],
];
export const VIEWPORT_LARGEST_BUCKET = "xl";

export const BROWSER_FAMILY_PATTERNS: ReadonlyArray<readonly [string, RegExp]> =
  [
    ["edge", /Edg\//],
    ["firefox", /Firefox\//],
    ["chrome", /Chrome\//],
    ["safari", /Safari\//],
  ];
export const BROWSER_FAMILY_OTHER = "other";
