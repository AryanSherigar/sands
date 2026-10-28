interface DiscoveredLocation {
  entityId: string;
  name: string;
}

export interface DiscoveredLocationListProps {
  locations: DiscoveredLocation[];
  currentLocationId?: string;
}
