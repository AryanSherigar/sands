import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_CONFIG } from "@/test/alphaFixtures";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { AlphaIntakeGate } from "../AlphaIntakeGate/AlphaIntakeGate";
import { PostRunSurvey } from "../PostRunSurvey/PostRunSurvey";

const USER_ID = "user-1";

function captureSurveys(status = 201): unknown[] {
  const received: unknown[] = [];
  server.use(
    http.post("*/v1/alpha/survey", async ({ request }) => {
      received.push(await request.json());
      return HttpResponse.json({ kind: "intake" }, { status });
    }),
  );
  return received;
}

describe("AlphaIntakeGate", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({
      user: { user_id: USER_ID, display_name: "T", onboarding_completed: true },
    });
  });

  it("asks both questions once and sends the answers", async () => {
    const received = captureSurveys();
    const user = userEvent.setup();
    render(<AlphaIntakeGate />, { wrapper: createQueryWrapper(ALPHA_CONFIG) });

    await user.selectOptions(screen.getByLabelText(/how much horror/i), "some");
    await user.selectOptions(screen.getByLabelText(/what do you usually play on/i), "phone");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(received).toEqual([
        {
          kind: "intake",
          answers: { horror_experience: "some", usual_device: "phone" },
        },
      ]),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("can be skipped and does not come back", async () => {
    const received = captureSurveys();
    const user = userEvent.setup();
    const { unmount } = render(<AlphaIntakeGate />, {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });

    await user.click(screen.getByRole("button", { name: "Skip" }));
    unmount();
    render(<AlphaIntakeGate />, { wrapper: createQueryWrapper(ALPHA_CONFIG) });

    expect(received).toEqual([]);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("treats an already-answered survey (409) as done", async () => {
    captureSurveys(409);
    const user = userEvent.setup();
    render(<AlphaIntakeGate />, { wrapper: createQueryWrapper(ALPHA_CONFIG) });

    await user.selectOptions(screen.getByLabelText(/how much horror/i), "none");
    await user.selectOptions(screen.getByLabelText(/what do you usually play on/i), "tablet");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});

describe("PostRunSurvey", () => {
  it("needs both ratings before it can be sent", async () => {
    const user = userEvent.setup();
    render(<PostRunSurvey playthroughId="pt-1" isOpen onClose={vi.fn()} />, {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });
    const send = screen.getByRole("button", { name: "Send" });
    expect(send).toBeDisabled();

    await user.click(
      screen.getByRole("radiogroup", { name: /Overall rating/ }).querySelector('button[aria-checked]') as HTMLElement,
    );

    expect(send).toBeDisabled();
  });

  it("sends the ratings and notes, then closes", async () => {
    const received = captureSurveys();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<PostRunSurvey playthroughId="pt-1" isOpen onClose={onClose} />, {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });

    const overall = screen.getByRole("radiogroup", { name: /Overall rating/ });
    const scary = screen.getByRole("radiogroup", { name: /How scary/ });
    await user.click(overall.querySelectorAll("button")[3] as HTMLElement);
    await user.click(scary.querySelectorAll("button")[4] as HTMLElement);
    await user.type(screen.getByLabelText("Anything confusing?"), "the phone");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(received).toEqual([
      {
        kind: "post_run",
        playthrough_id: "pt-1",
        answers: { rating: 4, scariness: 5, confusing: "the phone" },
      },
    ]);
  });

  it("closes without sending when skipped", async () => {
    const received = captureSurveys();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<PostRunSurvey playthroughId="pt-1" isOpen onClose={onClose} />, {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });

    await user.click(screen.getByRole("button", { name: "Skip" }));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(received).toEqual([]);
  });

  it("closes even when the endpoint says it was already answered (409)", async () => {
    captureSurveys(409);
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<PostRunSurvey playthroughId="pt-1" isOpen onClose={onClose} />, {
      wrapper: createQueryWrapper(ALPHA_CONFIG),
    });
    const overall = screen.getByRole("radiogroup", { name: /Overall rating/ });
    const scary = screen.getByRole("radiogroup", { name: /How scary/ });
    await user.click(overall.querySelectorAll("button")[0] as HTMLElement);
    await user.click(scary.querySelectorAll("button")[0] as HTMLElement);

    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });
});
