export interface OnboardingPayload {
  display_name?: string;
  bio?: string;
  avatar_url?: string;
  banner_url?: string;
  preferred_genres: string[];
}

export interface OnboardingResult {
  display_name: string;
  preferred_genres: string[];
  onboarding_completed_at: string | null;
}

export interface OnboardingProfileDraft {
  display_name: string;
  bio: string | null;
  avatar_url: string | null;
  banner_url: string | null;
  preferred_genres: string[];
}
