import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MapViewer } from "../MapViewer";

const DESK_ID = "entity-desk";
const CORRIDOR_ID = "entity-corridor";
const MAP_ID = "map-1";

function buildSnapshot(imageUrl: string | null): Record<string, unknown> {
  return {
    maps: [{ map_id: MAP_ID, name: "Floor 9", image_url: imageUrl }],
    map_pins: [
      { pin_id: "p1", map_id: MAP_ID, entity_id: DESK_ID, x: 0.2, y: 0.2 },
      { pin_id: "p2", map_id: MAP_ID, entity_id: CORRIDOR_ID, x: 0.5, y: 0.5 },
    ],
    map_connections: [],
    entities: [
      { entity_id: DESK_ID, canonical_name: "The night desk" },
      { entity_id: CORRIDOR_ID, canonical_name: "East corridor" },
    ],
  };
}

describe("MapViewer", () => {
  it("lists discovered locations when the map has no image", () => {
    render(
      <MapViewer
        scenarioSnapshot={buildSnapshot(null)}
        state={{
          current_location_id: DESK_ID,
          discovered_location_ids: [DESK_ID],
        }}
      />,
    );

    expect(screen.getByText("The night desk")).toBeInTheDocument();
    expect(screen.queryByText("East corridor")).not.toBeInTheDocument();
    expect(screen.queryByText(/Nothing discovered/)).not.toBeInTheDocument();
  });

  it("marks the current location in the text list", () => {
    render(
      <MapViewer
        scenarioSnapshot={buildSnapshot(null)}
        state={{
          current_location_id: CORRIDOR_ID,
          discovered_location_ids: [DESK_ID, CORRIDOR_ID],
        }}
      />,
    );

    expect(screen.getByText("East corridor")).toHaveAttribute(
      "aria-current",
      "location",
    );
    expect(screen.getByText("The night desk")).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("says nothing is discovered when no pin has been discovered", () => {
    render(
      <MapViewer
        scenarioSnapshot={buildSnapshot(null)}
        state={{ discovered_location_ids: [] }}
      />,
    );

    expect(screen.getByText(/Nothing discovered/)).toBeInTheDocument();
  });
});
