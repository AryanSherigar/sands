// Must equal SENSORY_CUE_IDS in apps/core-api/app/models/condition.py;
// apps/core-api/tests/test_frontend_constants_drift.py parses this file.
export const SENSORY_CUE_IDS = [
  "phone_ring",
  "heavy_knock",
  "light_buzz",
  "distant_footsteps",
  "sudden_silence",
  "radio_static",
  "elevator_chime",
  "lamp_click",
  "keyboard_typing",
  "paper_rustle",
] as const;

export type SensoryCueId = (typeof SENSORY_CUE_IDS)[number];

export const isSensoryCueId = (value: string): value is SensoryCueId =>
  (SENSORY_CUE_IDS as readonly string[]).includes(value);
