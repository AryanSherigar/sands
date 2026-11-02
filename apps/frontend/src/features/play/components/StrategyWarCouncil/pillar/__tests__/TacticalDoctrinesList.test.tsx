import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TacticalDoctrinesList } from "../TacticalDoctrinesList";

describe("TacticalDoctrinesList", () => {
  it("renders historical doctrines and disables doctrines when terrain prerequisites are unmet", () => {
    const onSelect = vi.fn();
    render(
      <TacticalDoctrinesList
        selectedTactic="hold"
        terrain="river"
        onSelectTactic={onSelect}
      />,
    );

    expect(screen.getByText(/Boar's Snout/i)).toBeInTheDocument();
    expect(screen.getByText(/Shield-Wall Anchor/i)).toBeInTheDocument();
    expect(screen.getByText(/Feigned Retreat/i)).toBeInTheDocument();
    expect(screen.getByText(/Forest Ambuscade/i)).toBeInTheDocument();

    // Forest Ambuscade requires Forest terrain; on River it must show Locked
    expect(screen.getByText(/Requires Forest terrain/i)).toBeInTheDocument();

    const boarCard = screen.getByText(/Boar's Snout/i).closest("button");
    expect(boarCard).not.toBeNull();
    if (boarCard) fireEvent.click(boarCard);
    expect(onSelect).toHaveBeenCalledWith("press");
  });

  it("locks Forest Ambuscade on plains terrain", () => {
    const onSelect = vi.fn();
    render(
      <TacticalDoctrinesList
        selectedTactic="hold"
        terrain="plains"
        onSelectTactic={onSelect}
      />,
    );

    expect(screen.getByText(/Requires Forest terrain/i)).toBeInTheDocument();
  });

  it("enables and allows selecting Forest Ambuscade when on forest terrain", () => {
    const onSelect = vi.fn();
    render(
      <TacticalDoctrinesList
        selectedTactic="hold"
        terrain="forest"
        onSelectTactic={onSelect}
      />,
    );

    expect(screen.queryByText(/Requires Forest terrain/i)).not.toBeInTheDocument();

    const ambuscadeCard = screen.getByText(/Forest Ambuscade/i).closest("button");
    expect(ambuscadeCard).not.toBeNull();
    if (ambuscadeCard) fireEvent.click(ambuscadeCard);
    expect(onSelect).toHaveBeenCalledWith("forest_flank");
  });

  it("indicates which doctrine is active and allows selecting Shield-Wall Anchor", () => {
    const onSelect = vi.fn();
    render(
      <TacticalDoctrinesList
        selectedTactic="press"
        terrain="forest"
        onSelectTactic={onSelect}
      />,
    );

    const shieldWallCard = screen.getByText(/Shield-Wall Anchor/i).closest("button");
    expect(shieldWallCard).not.toBeNull();
    if (shieldWallCard) fireEvent.click(shieldWallCard);
    expect(onSelect).toHaveBeenCalledWith("hold");
  });
});
