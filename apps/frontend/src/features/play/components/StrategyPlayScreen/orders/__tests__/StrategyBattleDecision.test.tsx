import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { describe, it, expect, vi } from "vitest";
import { server } from "@/test/msw/server";
import { DEFAULT_PREVIEW_WORLD } from "../../defaultPreviewWorld";
import { StrategyBattleDecision } from "../StrategyBattleDecision";
import type { CampaignWorldView } from "../../../../types/simulation.types";

function mountDecision(onTakeCommand?: (battleId: string) => void) {
  const world: CampaignWorldView = { ...DEFAULT_PREVIEW_WORLD, status: "awaiting_battle_decision", wave: 0, world_version: 2, battles: [
    { id: "battle_1", region_id: "field", status: "awaiting_commands", exchanges_used: 0, total_exchanges: 0, is_big: true, control_mode: "undecided" },
  ] };
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  queryClient.setQueryData(["simulation-world", "pt-1"], world);
  render(<QueryClientProvider client={queryClient}><StrategyBattleDecision playthroughId="pt-1" world={world} regionNames={{ field: "Border Pass" }} onTakeCommand={onTakeCommand} /></QueryClientProvider>);
  return { queryClient, world };
}

describe("battle decision", () => {
  it("saves taking command without starting damage", async () => {
    const requests: unknown[] = [];
    server.use(http.post("*/simulation/v1/playthroughs/pt-1/commands", async ({ request }) => {
      requests.push(await request.json());
      return HttpResponse.json({ ...world, status: "awaiting_commands", world_version: 3, battles: [{ ...world.battles[0], control_mode: "player" }] });
    }));
    const { queryClient, world } = mountDecision();
    fireEvent.click(screen.getByRole("button", { name: "Take command" }));
    await waitFor(() => expect(queryClient.getQueryData<CampaignWorldView>(["simulation-world", "pt-1"])?.world_version).toBe(3));
    expect(requests[0]).toMatchObject({ expected_wave: 1, command: { kind: "take_command", battle_id: "battle_1" } });
  });

  it("opens the war council only after taking command has been saved", async () => {
    let release: () => void = () => undefined;
    const saved = new Promise<void>((resolve) => { release = resolve; });
    server.use(http.post("*/simulation/v1/playthroughs/pt-1/commands", async () => {
      await saved;
      return HttpResponse.json({ ...DEFAULT_PREVIEW_WORLD, status: "awaiting_commands", world_version: 3, battles: [{ id: "battle_1", region_id: "field", status: "awaiting_commands", exchanges_used: 0, total_exchanges: 0, is_big: true, control_mode: "player" }] });
    }));
    const onTakeCommand = vi.fn();
    mountDecision(onTakeCommand);
    fireEvent.click(screen.getByRole("button", { name: "Take command" }));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(onTakeCommand).not.toHaveBeenCalled();
    release();
    await waitFor(() => expect(onTakeCommand).toHaveBeenCalledWith("battle_1"));
  });

  it("does not open the war council when taking command fails", async () => {
    server.use(http.post("*/simulation/v1/playthroughs/pt-1/commands", () => HttpResponse.json({ detail: "Refresh and try again" }, { status: 409 })));
    const onTakeCommand = vi.fn();
    mountDecision(onTakeCommand);
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Take command" })));
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(onTakeCommand).not.toHaveBeenCalled();
  });

  it("delegates then continues with the response version and next-wave guard", async () => {
    const advances: unknown[] = [];
    server.use(
      http.post("*/simulation/v1/playthroughs/pt-1/commands", () => HttpResponse.json({ ...world, status: "awaiting_commands", world_version: 3, battles: [{ ...world.battles[0], control_mode: "delegated" }] })),
      http.post("*/simulation/v1/playthroughs/pt-1/battles/advance", async ({ request }) => {
        advances.push(await request.json());
        return HttpResponse.json({ ...world, status: "turn_completed", world_version: 4, turn: 1 });
      }),
    );
    const { queryClient, world } = mountDecision();
    fireEvent.click(screen.getByRole("button", { name: "Delegate and continue" }));
    await waitFor(() => expect(queryClient.getQueryData<CampaignWorldView>(["simulation-world", "pt-1"])?.status).toBe("turn_completed"));
    expect(advances).toHaveLength(1);
    expect(advances[0]).toMatchObject({ expected_world_version: 3, expected_wave: 1 });
  });

  it("shows a recoverable error when saving the choice fails", async () => {
    server.use(http.post("*/simulation/v1/playthroughs/pt-1/commands", () => HttpResponse.json({ detail: "Refresh and try again" }, { status: 409 })));
    mountDecision();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Take command" })));
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(screen.getByRole("button", { name: "Take command" })).toBeEnabled();
  });
});
