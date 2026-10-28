import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { usePlayStore } from "../../../../stores/play.store";
import type { PlaythroughData } from "../../../../types/play.types";
import { FeedbackButton } from "../FeedbackButton";

function seedRun(turns: number): void {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      turns: Array.from({ length: turns }, (_, index) => ({ id: `t-${index}` })),
    } as unknown as PlaythroughData,
  });
}

describe("FeedbackButton", () => {
  beforeEach(() => seedRun(3));

  it("renders nothing outside alpha mode", () => {
    render(<FeedbackButton />, { wrapper: createQueryWrapper(NON_ALPHA_CONFIG) });

    expect(screen.queryByRole("button", { name: "Feedback" })).toBeNull();
  });

  it("sends the category, text and current turn number", async () => {
    let received: unknown = null;
    server.use(
      http.post("*/v1/alpha/feedback", async ({ request }) => {
        received = await request.json();
        return HttpResponse.json({ feedback_id: "f-1" }, { status: 201 });
      }),
    );
    const user = userEvent.setup();
    render(<FeedbackButton />, { wrapper: createQueryWrapper(ALPHA_CONFIG) });

    await user.click(screen.getByRole("button", { name: "Feedback" }));
    await user.click(screen.getByRole("radio", { name: "Confusing" }));
    await user.type(screen.getByLabelText("What should we know?"), "The phone rule");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(received).toEqual({
        playthrough_id: "pt-1",
        turn_number: 3,
        category: "confusing",
        body: "The phone rule",
      }),
    );
  });

  it("will not send an empty note", async () => {
    const user = userEvent.setup();
    render(<FeedbackButton />, { wrapper: createQueryWrapper(ALPHA_CONFIG) });

    await user.click(screen.getByRole("button", { name: "Feedback" }));

    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });
});
