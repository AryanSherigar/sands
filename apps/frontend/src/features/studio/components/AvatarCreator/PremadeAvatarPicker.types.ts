import type { PremadeAvatar } from "../../types/premade_avatar.types";

export interface PremadeAvatarPickerProps {
  selectedAvatarUrl: string | null;
  onSelect: (avatar: PremadeAvatar) => void;
}
