import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { RuleCheckEditor } from "./RuleCheckEditor";

const API_URL = "http://localhost:8000";
const SCENARIO_ID = "scenario-1";
const BASE = `${API_URL}/v1/scenarios/${SCENARIO_ID}`;

const savedCheck = {
  check_id: "check-1",
  scenario_id: SCENARIO_ID,
  label: "Lamp-out",
  kind: "timed_choice",
  trigger_condition_expression: {},
  priority: 0,
  result_path: "check.lamp",
  narrator_instruction_template: null,
  params: {
    prompt: "The lamp has gone out.",
    options: [
      { id: "hold", label: "Hold still", result: "held", mutations: [], reopens: false },
      { id: "move", label: "Move away", result: "moved", mutations: [], reopens: false },
    ],
    window_ms: 12000,
    timeout_result: "timeout",
    hidden_result: null,
    max_reopens: 3,
  },
};

const mockBase = (checks: unknown[] = []): void => {
  server.use(
    http.get(`${BASE}`, () =>
      HttpResponse.json({
        scenario_id: SCENARIO_ID,
        state_schema: {
          check: {
            type: "object",
            fields: {
              lamp: {
                type: "enum",
                label: "Lamp answer",
                options: ["held", "moved", "timeout"],
                initial: "held",
              },
            },
          },
          sanity: { type: "number", label: "Sanity" },
        },
      }),
    ),
    http.get(`${BASE}/entities`, () => HttpResponse.json({ items: [] })),
    http.get(`${BASE}/rule-checks`, () => HttpResponse.json({ items: checks })),
  );
};

const renderEditor = (): void => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <RuleCheckEditor scenarioId={SCENARIO_ID} />
    </QueryClientProvider>,
  );
};

const fillNewCheck = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(await screen.findByRole("button", { name: /new rule check/i }));
  await user.type(screen.getByLabelText("Name"), "Lamp-out");
  await user.selectOptions(screen.getByLabelText("Answer is stored in"), "check.lamp");
  await user.type(screen.getByLabelText("Prompt"), "The lamp has gone out.");
  await user.type(screen.getByLabelText("Option 1 label"), "Hold still");
  await user.selectOptions(screen.getByLabelText("Option 1 result"), "held");
  await user.type(screen.getByLabelText("Option 2 label"), "Move away");
  await user.selectOptions(screen.getByLabelText("Option 2 result"), "moved");
  await user.selectOptions(screen.getByLabelText("Result when time runs out"), "timeout");
};

describe("RuleCheckEditor", () => {
  it("lists the saved checks with the field that stores each answer", async () => {
    mockBase([savedCheck]);
    renderEditor();

    expect(await screen.findByText("Lamp-out")).toBeInTheDocument();
    expect(screen.getByText(/stores its answer in check\.lamp/i)).toBeInTheDocument();
  });

  it("shows a time entry check read-only and still lets it be deleted", async () => {
    mockBase([
      {
        ...savedCheck,
        check_id: "check-te",
        label: "Visitor log",
        kind: "time_entry",
        params: { prompt: "A visitor signs in.", window_ms: 20000 },
      },
    ]);
    renderEditor();

    const row = await screen.findByTestId("rule-check-row-check-te");

    expect(within(row).getByText("Time entry")).toBeInTheDocument();
    expect(
      within(row).getByText("This check type isn't editable in the form yet."),
    ).toBeInTheDocument();
    expect(within(row).queryByRole("button", { name: "Edit" })).toBeNull();
    expect(within(row).getByRole("button", { name: "Delete" })).toBeEnabled();
  });

  it("shows a time_entry check read-only with a note and no Edit button", async () => {
    mockBase([
      {
        ...savedCheck,
        check_id: "check-te",
        label: "Visitor log",
        kind: "time_entry",
        params: { prompt: "A visitor signs in.", window_ms: 20000 },
      },
    ]);
    renderEditor();

    const row = await screen.findByTestId("rule-check-row-check-te");

    expect(within(row).getByText("Visitor log")).toBeInTheDocument();
    expect(
      within(row).getByText("This check type isn't editable in the form yet."),
    ).toBeInTheDocument();
    expect(within(row).queryByRole("button", { name: "Edit" })).toBeNull();
    expect(within(row).getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("creates a timed choice and sends the window in milliseconds", async () => {
    mockBase();
    let captured: Record<string, unknown> | null = null;
    server.use(
      http.post(`${BASE}/rule-checks`, async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...savedCheck, ...captured, check_id: "new" });
      }),
    );
    const user = userEvent.setup();
    renderEditor();

    await fillNewCheck(user);
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(captured).toMatchObject({
      label: "Lamp-out",
      kind: "timed_choice",
      result_path: "check.lamp",
      params: {
        prompt: "The lamp has gone out.",
        window_ms: 12000,
        timeout_result: "timeout",
        hidden_result: null,
        options: [
          { label: "Hold still", result: "held" },
          { label: "Move away", result: "moved" },
        ],
      },
    });
  });

  it("keeps Save disabled and lists what is missing", async () => {
    mockBase();
    const user = userEvent.setup();
    renderEditor();

    await user.click(await screen.findByRole("button", { name: /new rule check/i }));

    expect(screen.getByRole("button", { name: /^save$/i })).toBeDisabled();
    expect(
      screen.getByText(/choose the tracked value that receives the answer/i),
    ).toBeInTheDocument();
  });

  it("warns below three seconds and shows the hidden-tab help", async () => {
    mockBase();
    const user = userEvent.setup();
    renderEditor();
    await user.click(await screen.findByRole("button", { name: /new rule check/i }));

    expect(screen.getByText(/leaves the tab for more than 1.5 s/i)).toBeInTheDocument();
    const slider = screen.getByLabelText("Window (seconds)");
    fireEvent.change(slider, { target: { value: "2" } });

    expect(screen.getByText(/under 3 seconds is very hard/i)).toBeInTheDocument();
  });

  it("shows the server's tool-not-enabled message with the tool name", async () => {
    mockBase();
    server.use(
      http.post(`${BASE}/rule-checks`, () =>
        HttpResponse.json(
          { detail: "Enable the 'rule_checks' tool for this scenario first", code: "tool_not_enabled" },
          { status: 409 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderEditor();

    await fillNewCheck(user);
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(await screen.findByText(/enable the 'rule_checks' tool/i)).toBeInTheDocument();
  });

  it("previews the prompt with the authored options using the player's component", async () => {
    mockBase();
    const user = userEvent.setup();
    renderEditor();

    await fillNewCheck(user);
    await user.click(screen.getByRole("button", { name: /preview prompt/i }));

    const preview = await screen.findByRole("dialog", { name: /preview prompt/i });
    expect(within(preview).getByText("The lamp has gone out.")).toBeInTheDocument();
    await user.click(within(preview).getByRole("button", { name: "Hold still" }));
    expect(within(preview).getByText(/chosen: hold still/i)).toBeInTheDocument();
  });

  it("builds a recall check with one original wording", async () => {
    mockBase();
    let captured: { params: Record<string, unknown> } | null = null;
    server.use(
      http.post(`${BASE}/rule-checks`, async ({ request }) => {
        captured = (await request.json()) as { params: Record<string, unknown> };
        return HttpResponse.json({ ...savedCheck, ...captured });
      }),
    );
    const user = userEvent.setup();
    renderEditor();
    await user.click(await screen.findByRole("button", { name: /new rule check/i }));

    await user.type(screen.getByLabelText("Name"), "Recall");
    await user.selectOptions(screen.getByLabelText("Kind"), "recall");
    await user.selectOptions(screen.getByLabelText("Answer is stored in"), "check.lamp");
    await user.type(screen.getByLabelText("Prompt"), "Which was it?");
    await user.type(screen.getByLabelText("Wording 1"), "original");
    await user.type(screen.getByLabelText("Wording 2"), "altered");
    await user.click(screen.getByLabelText("Wording 2 is the original"));
    await user.selectOptions(screen.getByLabelText("Result when correct"), "held");
    await user.selectOptions(screen.getByLabelText("Result when wrong"), "moved");
    await user.selectOptions(screen.getByLabelText("Result when time runs out"), "timeout");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(captured!.params).toMatchObject({
      variants: ["original", "altered"],
      correct_index: 1,
      result_correct: "held",
      result_wrong: "moved",
      result_timeout: "timeout",
    });
  });

  it("reorders and deletes", async () => {
    const second = { ...savedCheck, check_id: "check-2", label: "Phone" };
    mockBase([savedCheck, second]);
    let reordered: unknown = null;
    let deletedUrl = "";
    server.use(
      http.post(`${BASE}/rule-checks/reorder`, async ({ request }) => {
        reordered = await request.json();
        return HttpResponse.json({ items: [second, savedCheck] });
      }),
      http.delete(`${BASE}/rule-checks/check-1`, ({ request }) => {
        deletedUrl = request.url;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderEditor();

    await user.click(await screen.findByRole("button", { name: "Move Lamp-out down" }));
    expect(reordered).toEqual({ ordered_check_ids: ["check-2", "check-1"] });

    await user.click(
      within(await screen.findByTestId("rule-check-row-check-1")).getByRole("button", {
        name: "Delete",
      }),
    );
    expect(deletedUrl).toContain("/rule-checks/check-1");
  });
});
