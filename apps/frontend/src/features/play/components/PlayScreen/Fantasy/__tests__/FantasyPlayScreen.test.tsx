import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FantasyHeader } from "../FantasyHeader";
import { FantasyStatusStrip } from "../FantasyStatusStrip";
import { FantasyCharacterCard } from "../FantasyCharacterCard";
import { FantasyComposer } from "../FantasyComposer";
import { FantasyDossier } from "../FantasyDossier";
import { FantasyDossierResizer } from "../FantasyDossierResizer";
import { usePlayStore } from "../../../../stores/play.store";
import type { PlaythroughData } from "../../../../types/play.types";

describe("Fantasy UI Components", () => {
  describe("FantasyHeader", () => {
    it("renders dual tiers with scenario title and folios", () => {
      const onBack = vi.fn();
      const onToggleDossier = vi.fn();
      render(
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <FantasyHeader
          scenarioTitle="The Gilded Crown"
          folioTitle="FOLIO II · THE ASHEN REACH"
          turnNumber={18}
          isNarrating={false}
          isDossierOpen={false}
          dossierButton={{ current: null as unknown as HTMLButtonElement }}
          onBack={onBack}
          onOpenCodex={vi.fn()}
          onOpenChronicle={vi.fn()}
          onToggleDossier={onToggleDossier}
        />
        </QueryClientProvider>
      );
      expect(screen.getByText("The Gilded Crown")).toBeInTheDocument();
      expect(screen.getByText(/FOLIO II · THE ASHEN REACH/)).toBeInTheDocument();
      expect(screen.getByText(/CHRONICLE TURN 18/)).toBeInTheDocument();
      expect(screen.getByText("World Dossier")).toBeInTheDocument();
    });
  });

  describe("FantasyStatusStrip", () => {
    it("renders locale, energy, and vault status", () => {
      render(
        <FantasyStatusStrip
          status={{
            locale: "The Hearth & Anchor Tavern",
            energy: { current: 85, max: 100 },
            vault: { coins: 142, label: "142 Imperial Sovereigns" },
          }}
        />
      );
      expect(screen.getByText("The Hearth & Anchor Tavern")).toBeInTheDocument();
      expect(screen.getByText("85 / 100")).toBeInTheDocument();
      expect(screen.getByText(/142 Imperial Sovereigns/)).toBeInTheDocument();
    });
  });

  describe("FantasyCharacterCard", () => {
    const character = {
      id: "valerie",
      name: "Captain Valerie Vane",
      role: "Vanguard",
      title: "Vanguard Commander · Iron Legion",
      bio: "Hardened veteran of the Ashen Marshes.",
      disposition: { percent: 64, label: "64% Receptive" },
      tacticalRole: "Heavy Bulwark",
      currentMood: "Guarded",
      initial: "V",
      attributes: [{ label: "Tactical Role", value: "Heavy Bulwark" }],
    };

    it("renders compact card and handles expand", () => {
      const onToggle = vi.fn();
      render(
        <FantasyCharacterCard
          character={character}
          isExpanded={false}
          canTalk={true}
          onToggleExpand={onToggle}
          onTalk={vi.fn()}
        />
      );
      expect(screen.getByText("Captain Valerie Vane")).toBeInTheDocument();
      expect(screen.getByText("64% Receptive")).toBeInTheDocument();
      fireEvent.click(screen.getByText("Expand"));
      expect(onToggle).toHaveBeenCalled();
    });

    it("renders expanded card with action buttons", () => {
      const onTalk = vi.fn();
      render(
        <FantasyCharacterCard
          character={character}
          isExpanded={true}
          canTalk={true}
          onToggleExpand={vi.fn()}
          onTalk={onTalk}
        />
      );
      expect(screen.getByText("Expanded Folio Dossier")).toBeInTheDocument();
      expect(screen.getByText("Heavy Bulwark")).toBeInTheDocument();
      fireEvent.click(screen.getByText("Confer Privately"));
      expect(onTalk).toHaveBeenCalledWith("Captain Valerie Vane");
    });
  });

  describe("FantasyComposer", () => {
    it("submits deed and toggles tactical chips", () => {
      const onSubmit = vi.fn();
      const onContinue = vi.fn();
      render(
        <FantasyComposer
          tacticalInclinations={["Inquire about the runic cylinder"]}
          isNarrating={false}
          canRetry={false}
          onSubmit={onSubmit}
          onContinue={onContinue}
          onRetry={vi.fn()}
        />
      );
      expect(screen.getByText("Deed (Do)")).toBeInTheDocument();
      expect(screen.getByText("Seal & Inscribe")).toBeInTheDocument();

      // Inclinations are visible by default; toggle Hide then Show
      expect(screen.getByText(/"Inquire about the runic cylinder"/)).toBeInTheDocument();
      fireEvent.click(screen.getByText("Hide"));
      expect(screen.queryByText(/"Inquire about the runic cylinder"/)).not.toBeInTheDocument();
      fireEvent.click(screen.getByText("Show"));
      expect(screen.getByText(/"Inquire about the runic cylinder"/)).toBeInTheDocument();

      // Click chip
      fireEvent.click(screen.getByText(/"Inquire about the runic cylinder"/));
      fireEvent.click(screen.getByText("Seal & Inscribe"));
      expect(onSubmit).toHaveBeenCalledWith("Inquire about the runic cylinder");
    });
  });

  describe("FantasyDossier", () => {
    beforeEach(() => {
      usePlayStore.setState({
        playthrough: {
          entities: [],
          turns: [],
          state: {},
          player_inventory: [],
          objectives: [],
          action_chips: [],
        } as unknown as PlaythroughData,
      });
    });

    it("renders dossier tabs and archives button", () => {
      const onOpenCodex = vi.fn();
      render(
        <MemoryRouter>
          <FantasyDossier
            playthrough={usePlayStore.getState().playthrough!}
            onClose={vi.fn()}
            onTalk={vi.fn()}
            onOpenCodex={onOpenCodex}
          />
        </MemoryRouter>
      );
      expect(screen.getByText("World Dossier")).toBeInTheDocument();
      expect(screen.getByText("Party & NPCs")).toBeInTheDocument();
      expect(screen.getByText("Examine Complete Folio Archives")).toBeInTheDocument();
      fireEvent.click(screen.getByText("Examine Complete Folio Archives"));
      expect(onOpenCodex).toHaveBeenCalled();
    });
  });

  describe("FantasyDossierResizer", () => {
    it("renders separator with correct aria attributes and handles drag and keyboard", () => {
      const onStartDrag = vi.fn();
      const onKeyDown = vi.fn();
      render(
        <FantasyDossierResizer
          sidebarWidth={420}
          minWidth={340}
          maxWidth={640}
          isDragging={false}
          onStartDrag={onStartDrag}
          onKeyDown={onKeyDown}
        />
      );

      const resizer = screen.getByRole("separator", { name: "Resize Crown Dossier" });
      expect(resizer).toHaveAttribute("aria-valuenow", "420");
      expect(resizer).toHaveAttribute("aria-valuemin", "340");
      expect(resizer).toHaveAttribute("aria-valuemax", "640");

      fireEvent.mouseDown(resizer);
      expect(onStartDrag).toHaveBeenCalled();

      fireEvent.keyDown(resizer, { key: "ArrowLeft" });
      expect(onKeyDown).toHaveBeenCalled();
    });
  });
});

describe("fantasy presentation integrity", () => {
  it("does not show reference captions on another scene", async () => {
    const { FantasyScenePlate } = await import("../FantasyScenePlate");
    render(<FantasyScenePlate url="https://example.com/scene.jpg" />);
    expect(screen.queryByText(/HEARTH & ANCHOR GUILDHALL/)).not.toBeInTheDocument();
    expect(screen.queryByText(/IMPERIAL YEAR/)).not.toBeInTheDocument();
  });

  it("exposes a compact character as a keyboard-accessible button", () => {
    const onToggle = vi.fn();
    render(<FantasyCharacterCard character={{ id: "a", name: "Veya", role: "", title: "", bio: null, disposition: null, initial: "V", attributes: [] }} isExpanded={false} canTalk onToggleExpand={onToggle} onTalk={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Veya/ }));
    expect(onToggle).toHaveBeenCalledOnce();
  });
});
