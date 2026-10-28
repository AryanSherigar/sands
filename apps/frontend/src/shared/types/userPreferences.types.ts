// Deliberately narrow: features/play/ cannot import from features/profile/
// (feature-boundary rule), so this mirrors just the one field of
// features/profile/types/profile.types.ts::UserProfile that play needs,
// rather than promoting the whole profile type to shared/.
export interface VoiceOutputPreference {
  voice_output_enabled: boolean;
}

export interface MaturePreference {
  show_mature: boolean;
}

export interface AccountSummary {
  created_at: string;
}
