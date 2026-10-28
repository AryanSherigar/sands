import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { SheetRuleEditor } from "./SheetRuleEditor";

const BASE = "http://localhost:8000/v1/scenarios/scenario-1";

const rule = (number: number, key: string, text: string) => ({
  rule_id: `rule-${number}`,
  scenario_id: "scenario-1",
  key,
  number,
  text,
  corrupted_text: null,
  initial_status: "intact",
  source_style: "typed",
  is_ai_flaggable: false,
  display_order: number - 1,
});

const renderEditor = (): void => {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <SheetRuleEditor scenarioId="scenario-1" />
    </QueryClientProvider>,
  );
};

describe("SheetRuleEditor", () => {
  it("lists the rules and previews the clipboard with a status toggle", async () => {
    server.use(
      http.get(`${BASE}/sheet-rules`, () =>
        HttpResponse.json({ items: [rule(1, "r1", "Sign the Log.")] }),
      ),
    );
    const user = userEvent.setup();
    renderEditor();

    expect((await screen.findAllByText("Sign the Log.")).length).toBeGreaterThan(1);
    await user.selectOptions(
      screen.getByLabelText("Preview status of rule 1"),
      "violated",
    );
    expect(screen.getByLabelText("Preview status of rule 1")).toHaveValue("violated");
  });

  it("creates a rule with the suggested key and number", async () => {
    let captured: Record<string, unknown> | null = null;
    server.use(
      http.get(`${BASE}/sheet-rules`, () => HttpResponse.json({ items: [] })),
      http.post(`${BASE}/sheet-rules`, async ({ request }) => {
        captured = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(rule(1, "r1", "Sign the Log."));
      }),
    );
    const user = userEvent.setup();
    renderEditor();

    await user.click(await screen.findByRole("button", { name: /new rule/i }));
    await user.type(screen.getByLabelText("Rule text"), "Sign the Log.");
    await user.selectOptions(screen.getByLabelText("Written in"), "pencil");
    await user.click(screen.getByLabelText(/narrator may report breaking/i));
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(captured).toMatchObject({
      key: "r1",
      number: 1,
      text: "Sign the Log.",
      source_style: "pencil",
      is_ai_flaggable: true,
      initial_status: "intact",
      corrupted_text: null,
    });
  });

  it("refuses a duplicate key and shows the server's error", async () => {
    server.use(
      http.get(`${BASE}/sheet-rules`, () =>
        HttpResponse.json({ items: [rule(1, "r1", "Sign the Log.")] }),
      ),
      http.post(`${BASE}/sheet-rules`, () =>
        HttpResponse.json(
          { detail: "Enable the 'rule_sheet' tool for this scenario first" },
          { status: 409 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderEditor();

    await user.click(await screen.findByRole("button", { name: /new rule/i }));
    await user.clear(screen.getByLabelText("Key"));
    await user.type(screen.getByLabelText("Key"), "r1");
    await user.type(screen.getByLabelText("Rule text"), "x");
    expect(screen.getByText(/already used/i)).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Key"));
    await user.type(screen.getByLabelText("Key"), "r2");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(await screen.findByText(/enable the 'rule_sheet' tool/i)).toBeInTheDocument();
  });
});
