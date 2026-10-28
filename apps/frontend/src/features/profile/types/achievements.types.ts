export interface AchievementProgress {
  current: number;
  target: number;
}

export interface OwnerAchievementDto {
  key: string;
  name: string;
  family: string;
  requirement: string;
  earned_at: string | null;
  progress: AchievementProgress;
}

export interface PublicAchievementDto {
  key: string;
  name: string;
  family: string;
  requirement: string;
  earned_at: string;
}

export interface AchievementItem {
  key: string;
  name: string;
  family: string;
  requirement: string;
  earned_at: string | null;
  progress: AchievementProgress | null;
}
