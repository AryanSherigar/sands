export interface ScenarioInviteResponse {
  url: string;
  expires_at: string;
}

export interface ScenarioInviteAcceptResponse {
  scenario_id: string;
}

export interface ScenarioAccessMember {
  user_id: string;
  display_name: string;
}
