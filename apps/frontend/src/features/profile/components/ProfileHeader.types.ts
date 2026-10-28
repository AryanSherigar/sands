import type { UserProfile } from "../types/profile.types";

export interface ProfileHeaderProps {
  profile: UserProfile;
  isOwner: boolean;
  onEditClick: () => void;
}
