export interface MapViewerProps {
  embedded?: boolean;
  scenarioSnapshot: Record<string, unknown> | undefined;
  state: Record<string, unknown> | undefined;
}
