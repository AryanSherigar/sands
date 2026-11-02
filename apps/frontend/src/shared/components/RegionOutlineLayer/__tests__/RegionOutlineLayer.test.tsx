import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { RegionOutlineLayer } from "../RegionOutlineLayer";
import type { MapDocument } from "@/shared/types/strategy-map.types";

const mockDocument: MapDocument = {
  schema_version: 1,
  source: "manual",
  width: 1000,
  height: 500,
  image_url: null,
  regions: [
    {
      id: "reg-1",
      name: "Northland",
      terrain: "plain",
      outline: "M0 0 L10 0 L10 10 Z",
      label_point: { x: 5, y: 5 },
      neighbor_ids: ["reg-2"],
      source_color: null,
      source_ref: null,
    },
    {
      id: "reg-2",
      name: "Southland",
      terrain: "forest",
      outline: "M10 0 L20 0 L20 10 Z",
      label_point: { x: 15, y: 5 },
      neighbor_ids: ["reg-1"],
      source_color: null,
      source_ref: null,
    },
  ],
  roads: [],
};

const defaultProps = {
  document: mockDocument,
  targetSize: { width: 1000, height: 500 },
  selectedIds: [],
};

describe("RegionOutlineLayer", () => {
  it("applies default idle stroke class when region is not selected", () => {
    const { container } = render(
      <svg>
        <RegionOutlineLayer {...defaultProps} />
      </svg>,
    );

    const path = container.querySelector('[data-region-id="reg-1"]');
    expect(path).toHaveClass("stroke-white/70", "stroke-1");
  });

  it("applies custom stroke classes via regionStrokeClasses", () => {
    const { container } = render(
      <svg>
        <RegionOutlineLayer
          {...defaultProps}
          regionStrokeClasses={{
            "reg-1": "stroke-sky-400 stroke-2",
            "reg-2": "stroke-amber-400 stroke-1",
          }}
        />
      </svg>,
    );

    const path1 = container.querySelector('[data-region-id="reg-1"]');
    const path2 = container.querySelector('[data-region-id="reg-2"]');

    expect(path1).toHaveClass("stroke-sky-400", "stroke-2");
    expect(path1).not.toHaveClass("stroke-white/70");
    expect(path2).toHaveClass("stroke-amber-400", "stroke-1");
  });

  it("prioritizes selected class over regionStrokeClasses", () => {
    const { container } = render(
      <svg>
        <RegionOutlineLayer
          {...defaultProps}
          selectedIds={["reg-1"]}
          regionStrokeClasses={{
            "reg-1": "stroke-sky-400 stroke-2",
          }}
        />
      </svg>,
    );

    const path1 = container.querySelector('[data-region-id="reg-1"]');
    expect(path1).toHaveClass("stroke-primary", "stroke-2");
    expect(path1).not.toHaveClass("stroke-sky-400");
  });

  it("falls back to idle class when region is omitted from regionStrokeClasses", () => {
    const { container } = render(
      <svg>
        <RegionOutlineLayer
          {...defaultProps}
          regionStrokeClasses={{
            "reg-1": "stroke-sky-400 stroke-2",
          }}
        />
      </svg>,
    );

    const path2 = container.querySelector('[data-region-id="reg-2"]');
    expect(path2).toHaveClass("stroke-white/70", "stroke-1");
  });

  it("handles region clicks", () => {
    const handleClick = vi.fn();
    const { container } = render(
      <svg>
        <RegionOutlineLayer {...defaultProps} onRegionClick={handleClick} />
      </svg>,
    );

    const path1 = container.querySelector('[data-region-id="reg-1"]');
    expect(path1).not.toBeNull();
    if (path1) {
      fireEvent.click(path1);
      expect(handleClick).toHaveBeenCalledTimes(1);
      expect(handleClick).toHaveBeenCalledWith("reg-1", expect.any(Object));
    }
  });
});
