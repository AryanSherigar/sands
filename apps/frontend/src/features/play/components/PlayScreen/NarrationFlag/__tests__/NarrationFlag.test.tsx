import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { NarrationFlag } from "../NarrationFlag";

const TURN_ID = "3f2b8a4e-1c9d-4e7a-9b6f-0a1b2c3d4e5f";

function captureFlags(): unknown[] {
  const received: unknown[] = [];
  server.use(
    http.post(`*/v1/alpha/turns/${TURN_ID}/flag`, async ({ request }) => {
      received.push(await request.json());
      return HttpResponse.json({ flag_id: "x", turn_id: TURN_ID, reasons: [] });
    }),
  );
  return received;
}

describe("NarrationFlag", () => {
  it("renders nothing outside alpha mode", () => {
    render(<NarrationFlag turnId={TURN_ID} />, {
      wrapper: createQueryWrapper(NON_ALPHA_CONFIG),
    });

    expect(screen.queryByRole("button")).toBeNull();
  });

  it("waits for a saved turn id before offering a flag", () => {
    render(<NarrationFlag turnId="local-1700000000000" />, {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });

    expect(screen.queryByRole("button")).toBeNull();
  });

  it("flags a broken rule in one tap", async () => {
    const received = captureFlags();
    const user = userEvent.setup();
    render(<NarrationFlag turnId={TURN_ID} />, {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });

    await user.click(screen.getByRole("button", { name: "This broke a rule" }));

    await waitFor(() => expect(received).toEqual([{ reasons: ["broke_rule"] }]));
    expect(await screen.findByText(/Flagged/)).toBeInTheDocument();
  });

  it("sends the chosen reasons and note from the detail panel", async () => {
    const received = captureFlags();
    const user = userEvent.setup();
    render(<NarrationFlag turnId={TURN_ID} />, {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });

    await user.click(screen.getByRole("button", { name: "Something else" }));
    await user.click(screen.getByLabelText("Too long"));
    await user.click(screen.getByLabelText("Out of character"));
    await user.type(screen.getByLabelText("Note"), "rambling");
    await user.click(screen.getByRole("button", { name: "Send flag" }));

    await waitFor(() =>
      expect(received).toEqual([
        { reasons: ["too_long", "out_of_character"], note: "rambling" },
      ]),
    );
  });
});
