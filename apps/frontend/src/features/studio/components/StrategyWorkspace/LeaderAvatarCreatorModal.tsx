import { AvatarCreatorModal } from "../AvatarCreator/AvatarCreatorModal";

interface LeaderAvatarCreatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  leaderName: string;
  factionName: string;
  currentAvatarUrl?: string | null;
  currentPortraitUrl?: string | null;
  onSave: (avatarUrl: string) => void;
  onSavePortrait?: (portraitUrl: string) => void;
}

export function LeaderAvatarCreatorModal({ leaderName, factionName, ...props }: LeaderAvatarCreatorModalProps) {
  return <AvatarCreatorModal {...props} characterName={leaderName} characterLabel={`${leaderName} of ${factionName}`} dialogLabel="Generate Animated Leader Avatar" attachLabel="Attach to Leader" />;
}
