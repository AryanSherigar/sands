import type { AvatarExpression } from "./RulerMeshAvatar.types";

export interface NegotiationRulerDossierProps {
  leaderName: string;
  factionName: string;
  portraitUrl?: string;
  avatarUrl?: string | null;
  expression?: AvatarExpression;
  isSpeaking?: boolean;
  traitIds?: string[];
  isAtWar?: boolean;
  playerLeaderName: string;
  playerFactionName: string;
  playerPortraitUrl?: string;
  playerGold: number;
  playerLevies: number;
}
