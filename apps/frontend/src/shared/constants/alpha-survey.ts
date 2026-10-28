import type {
  HorrorExperience,
  UsualDevice,
} from "@/shared/types/alphaSurvey.types";

export const RATING_VALUES = [1, 2, 3, 4, 5] as const;
export const SURVEY_FREE_TEXT_MAX_CHARS = 500;
export const INTAKE_DONE_STORAGE_PREFIX = "alpha_intake_survey_done:";

export const HORROR_EXPERIENCE_OPTIONS: ReadonlyArray<{
  value: HorrorExperience;
  label: string;
}> = [
  { value: "none", label: "New to horror" },
  { value: "some", label: "Some" },
  { value: "a_lot", label: "A lot" },
];

export const USUAL_DEVICE_OPTIONS: ReadonlyArray<{
  value: UsualDevice;
  label: string;
}> = [
  { value: "phone", label: "Phone" },
  { value: "tablet", label: "Tablet" },
  { value: "laptop_or_desktop", label: "Laptop or desktop" },
];
