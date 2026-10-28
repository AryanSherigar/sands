// Must equal HINT_KINDS and CLOCK_FORMATS in
// apps/core-api/app/services/display_hints.py; apps/core-api/tests/
// test_frontend_constants_drift.py parses these arrays.
export const DISPLAY_HINT_KINDS = ["clock", "meter", "tier"] as const;
export const CLOCK_FORMATS = ["12h", "24h"] as const;

