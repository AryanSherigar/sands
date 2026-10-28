import type {
  ReaderFontSize,
  ReaderLineHeight,
  ReaderTheme,
} from "@/shared/types/readerPreferences.types";
import {
  INPUT_STEP_IDS,
  ONBOARDING_STEP_IDS,
} from "../constants/onboarding.constants";

export type OnboardingStepId = (typeof ONBOARDING_STEP_IDS)[number];
export type InputStepId = (typeof INPUT_STEP_IDS)[number];

export interface OnboardingDraft {
  genres: string[];
  displayName: string;
  bio: string;
  avatarUrl: string | null;
  bannerUrl: string | null;
  readerTheme: ReaderTheme;
  readerFontId: string | null;
  readerFontSize: ReaderFontSize;
  readerLineHeight: ReaderLineHeight;
}
