import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { getWorldQueryKey } from "@/features/play/hooks/useSimulationCommands";
import type { CampaignWorldView } from "@/features/play/types/simulation.types";
import { server } from "@/test/msw/server";
import type { BattleView, ExchangeReport } from "../../StrategyWarCouncil.types";
import { useWarCouncilState } from "../useWarCouncilState";

const BASE = "/simulation/v1/playthroughs/pt-1";

const BATTLE: BattleView = {
  id: "b-ashford",
  region_id: "reg-ashford",
  status: "awaiting_commands",
  outcome: null,
  current_turn: 1,
  exchanges_used: 0,
  total_exchanges: 0,
  is_big: true,
  control_mode: "player",
  terrain: "river",
  weather: "rain",
  command_cost: 1,
  own_contingent: {
    faction_id: "f-player",
    army_ids: ["army-1"],
    troops: { infantry: 1800, archers_siege: 750, cavalry: 400 },
    morale: 85,
    fatigue: 10,
    plan: {
      formation: "balanced",
      tactic: "hold",
      withdrawal_policy: "balanced",
      reserve_policy: "conserve",
    },
    supply: "supplied",
    status: "fighting",
  },
  opponents: [{ faction_id: "f-rival", strength: { minimum: 1200, maximum: 1600 }, reports: [] }],
  legal_commands: ["set_plan", "commit_reserves", "withdraw", "reconnoitre"],
};

const REPORT: ExchangeReport = {
  battle_id: "b-ashford",
  campaign_turn: 1,
  exchange_index: 1,
  total_exchange: 1,
  own_losses: { infantry: 42 },
  opponent_strength: { minimum: 1100, maximum: 1500 },
  outcome: null,
};

const MUTATION = {
  playthrough_id: "pt-1",
  world_version: 5,
  world_hash: "hash",
  turn: 1,
  wave: 0,
  orders_remaining: 3,
  status: "awaiting_commands",
  battles: [],
  operation_id: "op",
};

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  client.setQueryData(getWorldQueryKey("pt-1"), {
    world_version: 4,
    turn: 1,
    wave: 0,
    status: "awaiting_commands",
  } as CampaignWorldView);
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function useBattleHandlers(reports: ExchangeReport[] = []) {
  server.use(
    http.get(`${BASE}/battles/b-ashford`, () => HttpResponse.json(BATTLE)),
    http.get(`${BASE}/battles/b-ashford/reports`, () => HttpResponse.json({ items: reports })),
  );
}

function renderCouncil() {
  return renderHook(() => useWarCouncilState("pt-1", "b-ashford"), { wrapper: createWrapper() });
}

describe("useWarCouncilState", () => {
  it("loads the battle from the API and exposes the commandable state", async () => {
    useBattleHandlers();
    const { result } = renderCouncil();

    await waitFor(() => expect(result.current.battle?.id).toBe("b-ashford"));

    expect(result.current.canCommitWave).toBe(true);
    expect(result.current.canWithdraw).toBe(true);
    expect(result.current.stagedPlan.tactic).toBe("hold");
  });

  it("reports a load failure instead of inventing a battle", async () => {
    server.use(
      http.get(`${BASE}/battles/b-ashford`, () => HttpResponse.json({}, { status: 500 })),
      http.get(`${BASE}/battles/b-ashford/reports`, () => HttpResponse.json({ items: [] })),
    );
    const { result } = renderCouncil();

    await waitFor(() => expect(result.current.loadErrorMessage).not.toBeNull());

    expect(result.current.battle).toBeUndefined();
  });

  it("sends set_plan with the operation guard then advances, and opens the latest report", async () => {
    useBattleHandlers([REPORT]);
    const bodies: Array<Record<string, unknown>> = [];
    server.use(
      http.post(`${BASE}/commands`, async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(MUTATION);
      }),
      http.post(`${BASE}/battles/advance`, async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(MUTATION);
      }),
    );
    const { result } = renderCouncil();
    await waitFor(() => expect(result.current.battle).toBeDefined());

    act(() => result.current.setActiveDoctrine("press"));
    await act(async () => {
      await result.current.commitWave();
    });

    expect(bodies[0]).toMatchObject({
      expected_world_version: 4,
      command: { kind: "set_plan", battle_id: "b-ashford", plan: { tactic: "press" } },
    });
    expect(bodies[1]).toMatchObject({ expected_world_version: 5 });
    expect(result.current.receiptReport?.exchange_index).toBe(1);
  });

  it("surfaces a rejected command and does not open a receipt", async () => {
    useBattleHandlers([REPORT]);
    server.use(
      http.post(`${BASE}/commands`, () =>
        HttpResponse.json({ detail: "Not enough command points." }, { status: 422 }),
      ),
    );
    const { result } = renderCouncil();
    await waitFor(() => expect(result.current.battle).toBeDefined());

    await act(async () => {
      await result.current.commitWave();
    });

    expect(result.current.commandErrorMessage).toBe("Not enough command points.");
    expect(result.current.receiptReport).toBeNull();
  });

  it("keeps the retreat modal open and shows the error when withdraw fails", async () => {
    useBattleHandlers();
    server.use(
      http.post(`${BASE}/commands`, () =>
        HttpResponse.json({ detail: "Withdrawal is not available." }, { status: 422 }),
      ),
    );
    const { result } = renderCouncil();
    await waitFor(() => expect(result.current.battle).toBeDefined());
    act(() => result.current.toggleRetreatModal());

    let didWithdraw = true;
    await act(async () => {
      didWithdraw = await result.current.confirmRetreat();
    });

    expect(didWithdraw).toBe(false);
    expect(result.current.isRetreatModalOpen).toBe(true);
    expect(result.current.commandErrorMessage).toBe("Withdrawal is not available.");
  });

  it("scouts the first opponent with a reconnoitre command", async () => {
    useBattleHandlers();
    const bodies: Array<Record<string, unknown>> = [];
    server.use(
      http.post(`${BASE}/commands`, async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json(MUTATION);
      }),
    );
    const { result } = renderCouncil();
    await waitFor(() => expect(result.current.battle).toBeDefined());

    await act(async () => {
      await result.current.orderScoutMission("reserves");
    });

    expect(bodies[0]).toMatchObject({
      command: { kind: "reconnoitre", subject_faction_id: "f-rival", target: "reserves" },
    });
    expect(result.current.noticeMessage).toBe("Outriders dispatched.");
  });

  it("offers the speech while address_troops is legal and posts it with the guard", async () => {
    server.use(
      http.get(`${BASE}/battles/b-ashford`, () =>
        HttpResponse.json({ ...BATTLE, legal_commands: [...BATTLE.legal_commands, "address_troops"] }),
      ),
      http.get(`${BASE}/battles/b-ashford/reports`, () => HttpResponse.json({ items: [] })),
    );
    const bodies: Array<Record<string, unknown>> = [];
    server.use(
      http.post("/trs/v1/strategy/playthroughs/pt-1/battles/b-ashford/speech/reaction", () =>
        HttpResponse.json({ line: "A veteran grunts and nods." }),
      ),
      http.post(`${BASE}/battles/b-ashford/speech`, async ({ request }) => {
        bodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({ mutation: MUTATION, reception: "stirred" });
      }),
    );
    const { result } = renderCouncil();
    await waitFor(() => expect(result.current.canAddressTroops).toBe(true));

    await act(async () => {
      await result.current.addressTroops("Hold the line.");
    });

    expect(bodies[0]).toMatchObject({ speech_text: "Hold the line.", expected_world_version: 4 });
    expect(result.current.speechReception).toBe("stirred");
    await waitFor(() => expect(result.current.speechReactionLine).toBe("A veteran grunts and nods."));
  });

  it("surfaces a speech failure and stays open", async () => {
    useBattleHandlers();
    server.use(
      http.post(`${BASE}/battles/b-ashford/speech`, () =>
        HttpResponse.json({ detail: "The troops cannot be addressed now." }, { status: 422 }),
      ),
    );
    const { result } = renderCouncil();
    await waitFor(() => expect(result.current.battle).toBeDefined());

    let didSpeak = true;
    await act(async () => {
      didSpeak = await result.current.addressTroops("Words.");
    });

    expect(didSpeak).toBe(false);
    expect(result.current.speechErrorMessage).toBe("The troops cannot be addressed now.");
  });
});
