import { create } from "zustand";

export interface PlaytestTurn {
  id: string;
  actionText: string;
  narration: string;
}

interface PendingPlaytestTest {
  overrides: Record<string, unknown>;
  note: string | null;
}

interface PlaytestSessionStart {
  scenarioId: string;
  playthroughId: string;
  participantId: string;
  openingText: string;
  startedStamp: string | null;
  setupValues: Record<string, unknown>;
  state: Record<string, unknown>;
  note: string | null;
}

interface PlaytestState {
  scenarioId: string | null;
  playthroughId: string | null;
  participantId: string | null;
  openingText: string;
  startedStamp: string | null;
  setupValues: Record<string, unknown>;
  state: Record<string, unknown>;
  note: string | null;
  pendingTest: PendingPlaytestTest | null;
  turns: PlaytestTurn[];
  requestTest: (test: PendingPlaytestTest) => void;
  clearPendingTest: () => void;
  setState: (state: Record<string, unknown>) => void;
  beginSession: (session: PlaytestSessionStart) => void;
  appendTurn: (turn: Omit<PlaytestTurn, "id">) => void;
  endSession: () => void;
}

const EMPTY_SESSION = {
  scenarioId: null,
  playthroughId: null,
  participantId: null,
  openingText: "",
  startedStamp: null,
  setupValues: {},
  state: {},
  note: null,
  turns: [],
};

export const usePlaytestStore = create<PlaytestState>((set) => ({
  ...EMPTY_SESSION,
  pendingTest: null,
  requestTest: (test) => set({ pendingTest: test }),
  clearPendingTest: () => set({ pendingTest: null }),
  setState: (state) => set({ state }),
  beginSession: (session) => set({ ...EMPTY_SESSION, ...session }),
  appendTurn: (turn) =>
    set((state) => ({
      turns: [...state.turns, { ...turn, id: crypto.randomUUID() }],
    })),
  endSession: () => set(EMPTY_SESSION),
}));
