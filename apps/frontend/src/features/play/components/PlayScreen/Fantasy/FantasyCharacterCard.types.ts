import type { FantasyCharacter } from "../../../utils/buildFantasyViewModel";

export interface FantasyCharacterCardProps {
  character: FantasyCharacter;
  isExpanded: boolean;
  canTalk: boolean;
  onToggleExpand: () => void;
  onTalk: (characterName: string) => void;
}
