import { UserResponse } from "@/features/auth/types/auth.types";

export interface UserDropdownProps {
  user: UserResponse;
  onLogout: () => void;
}
