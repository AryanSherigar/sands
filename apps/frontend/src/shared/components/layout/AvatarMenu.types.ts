import type { UserResponse } from "@/features/auth/types/auth.types";

export interface AvatarMenuProps {
  user: UserResponse;
  onSignOut: () => void;
}
