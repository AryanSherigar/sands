import React from "react";
import { DiscoveredLocationListProps } from "./DiscoveredLocationList.types";

/** Text fallback for maps authored without an image. */
export const DiscoveredLocationList: React.FC<DiscoveredLocationListProps> = ({
  locations,
  currentLocationId,
}) => (
  <ul className="flex flex-col gap-1 p-1 text-xs">
    {locations.map((location) => {
      const isCurrent = location.entityId === currentLocationId;
      return (
        <li
          key={location.entityId}
          aria-current={isCurrent ? "location" : undefined}
          className={isCurrent ? "text-amber-200" : "text-zinc-300"}
        >
          {location.name}
        </li>
      );
    })}
  </ul>
);
