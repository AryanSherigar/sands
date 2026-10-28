export interface UserResponse {
  user_id: string;
  display_name: string;
  onboarding_completed: boolean;
  show_mature?: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
  is_account_restored?: boolean;
}
