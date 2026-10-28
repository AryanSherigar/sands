import type { NewTrackedValue } from "../types/trackedValue.types";

const NEW_OWN_VALUE_NAME = "New value";
export const DEFAULT_CLOCK_START = "09:00";
export const DEFAULT_CLOCK_FORMAT = "12h";
export const CLOCK_FORMAT_OPTIONS = [
  { value: "12h", label: "12-hour" },
  { value: "24h", label: "24-hour" },
] as const;

const HEALTH_LABEL = "Health";
const SANITY_LABEL = "Sanity";
const SCALE_MIN = 0;
const SCALE_MAX = 10;

export interface QuickAddValue {
  id: string;
  label: string;
  input: NewTrackedValue;
}

export const QUICK_ADD_VALUES: readonly QuickAddValue[] = [
  {
    id: "health",
    label: HEALTH_LABEL,
    input: {
      name: HEALTH_LABEL,
      kind: "number",
      min: SCALE_MIN,
      max: SCALE_MAX,
      initial: SCALE_MAX,
      display: { kind: "meter", label: HEALTH_LABEL, clamp_min: SCALE_MIN, clamp_max: SCALE_MAX },
    },
  },
  {
    id: "trust",
    label: "Trust",
    input: { name: "Trust", kind: "number", min: SCALE_MIN, max: SCALE_MAX, initial: 5 },
  },
  {
    id: "money",
    label: "Money",
    input: { name: "Money", kind: "number", min: 0, initial: 0 },
  },
  {
    id: "time",
    label: "Time",
    input: { name: "Time", kind: "enum", options: ["Dawn", "Day", "Dusk", "Night"] },
  },
  {
    id: "sanity",
    label: SANITY_LABEL,
    input: {
      name: SANITY_LABEL,
      kind: "number",
      min: SCALE_MIN,
      max: SCALE_MAX,
      initial: SCALE_MAX,
      display: {
        kind: "meter",
        label: SANITY_LABEL,
        clamp_min: SCALE_MIN,
        clamp_max: SCALE_MAX,
        tiers: [
          { name: "Steady", min: 7 },
          { name: "Shaken", min: 4 },
          { name: "Breaking" },
        ],
      },
    },
  },
];

export const OWN_VALUE_INPUT: NewTrackedValue = {
  name: NEW_OWN_VALUE_NAME,
  kind: "number",
  min: SCALE_MIN,
  max: SCALE_MAX,
  initial: SCALE_MIN,
};

export const DEFAULT_LEVELS = [
  { name: "High", min: 7 },
  { name: "Middle", min: 4 },
  { name: "Low" },
] as const;
