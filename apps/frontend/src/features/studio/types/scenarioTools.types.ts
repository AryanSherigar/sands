export interface ScenarioToolsResponse {
  enabled_tools: string[];
  auto_enabled: string[];
  inert_data: Record<string, number>;
}

export interface ScenarioToolsUpdate {
  enabled_tools: string[];
}
