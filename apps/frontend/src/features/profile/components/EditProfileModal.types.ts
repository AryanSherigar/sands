import type { UserProfile } from "../types/profile.types";

export interface EditProfileModalProps {
  profile: UserProfile;
  isOpen: boolean;
  onClose: () => void;
}
