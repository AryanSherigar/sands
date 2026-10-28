import { describe, expect, it } from "vitest";
import { selectCanRetryTurn } from "../play.selectors";

const IDLE_AFTER_ERROR = {
  is_narrating: false,
  is_turn_paused: false,
  last_client_action_id: "action-1",
  last_check_report: null,
};

describe("selectCanRetryTurn", () => {
  it("allows a retry after an error or an interrupted stream", () => {
    expect(selectCanRetryTurn(IDLE_AFTER_ERROR)).toBe(true);
  });

  it("allows a retry while a check report waits to be resent", () => {
    expect(
      selectCanRetryTurn({
        ...IDLE_AFTER_ERROR,
        last_client_action_id: null,
        last_check_report: { label: "Answer it" },
      }),
    ).toBe(true);
  });

  it("hides retry after a turn saved", () => {
    expect(
      selectCanRetryTurn({ ...IDLE_AFTER_ERROR, last_client_action_id: null }),
    ).toBe(false);
  });

  it("hides retry while the narrator is speaking", () => {
    expect(
      selectCanRetryTurn({ ...IDLE_AFTER_ERROR, is_narrating: true }),
    ).toBe(false);
  });

  it("hides retry while the owner has paused turns", () => {
    expect(
      selectCanRetryTurn({ ...IDLE_AFTER_ERROR, is_turn_paused: true }),
    ).toBe(false);
  });
});
