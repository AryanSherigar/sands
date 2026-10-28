import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { ToolsTab } from "./ToolsTab";

const API_URL = "http://localhost:8000";
const SCENARIO_ID = "scenario-1";
const TOOLS_URL = `${API_URL}/v1/scenarios/${SCENARIO_ID}/tools`;

interface ToolsState {
  enabled_tools: string[];
  auto_enabled: string[];
  inert_data: Record<string, number>;
}

const renderTab = (): void => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ToolsTab scenarioId={SCENARIO_ID} />
    </QueryClientProvider>,
  );
};

const serveTools = (initial: ToolsState): { puts: unknown[] } => {
  const puts: unknown[] = [];
  server.use(
    http.get(TOOLS_URL, () => HttpResponse.json(initial)),
    http.put(TOOLS_URL, async ({ request }) => {
      const body = (await request.json()) as { enabled_tools: string[] };
      puts.push(body);
      return HttpResponse.json({
        enabled_tools: body.enabled_tools,
        auto_enabled: [],
        inert_data: {},
      });
    }),
  );
  return { puts };
};

describe("ToolsTab", () => {
  it("lists every tool with its summary, all off by default", async () => {
    serveTools({ enabled_tools: [], auto_enabled: [], inert_data: {} });

    renderTab();

    expect(await screen.findByText("Rule checks")).toBeInTheDocument();
    expect(screen.getByText("Timed prompts and recall tests")).toBeInTheDocument();
    for (const toggle of screen.getAllByRole("switch")) {
      expect(toggle).not.toBeChecked();
    }
    expect(screen.getAllByRole("switch")).toHaveLength(5);
  });

  it("reflects the tools the server reports as enabled", async () => {
    serveTools({
      enabled_tools: ["status_hud"],
      auto_enabled: [],
      inert_data: {},
    });

    renderTab();

    expect(
      await screen.findByRole("switch", { name: /status hud/i }),
    ).toBeChecked();
  });

  it("sends the new list when a tool is switched on", async () => {
    const { puts } = serveTools({
      enabled_tools: [],
      auto_enabled: [],
      inert_data: {},
    });
    const user = userEvent.setup();
    renderTab();

    await user.click(await screen.findByRole("switch", { name: /rule checks/i }));

    expect(await screen.findByRole("switch", { name: /rule checks/i })).toBeChecked();
    expect(puts).toEqual([{ enabled_tools: ["rule_checks"] }]);
  });

  it("tells the creator when another tool was switched on for them", async () => {
    server.use(
      http.get(TOOLS_URL, () =>
        HttpResponse.json({ enabled_tools: [], auto_enabled: [], inert_data: {} }),
      ),
      http.put(TOOLS_URL, () =>
        HttpResponse.json({
          enabled_tools: ["status_hud", "atmosphere"],
          auto_enabled: ["status_hud"],
          inert_data: {},
        }),
      ),
    );
    const user = userEvent.setup();
    renderTab();

    await user.click(await screen.findByRole("switch", { name: /atmosphere/i }));

    expect(
      await screen.findByText(/status hud was also switched on/i),
    ).toBeInTheDocument();
  });

  it("blocks switching off a tool that an enabled tool needs", async () => {
    serveTools({
      enabled_tools: ["status_hud", "atmosphere"],
      auto_enabled: [],
      inert_data: {},
    });

    renderTab();

    const hud = await screen.findByRole("switch", { name: /status hud/i });
    expect(hud).toBeDisabled();
    expect(screen.getByText(/needed by atmosphere/i)).toBeInTheDocument();
  });

  it("warns that authored data of a disabled tool is inactive", async () => {
    serveTools({
      enabled_tools: [],
      auto_enabled: [],
      inert_data: { rule_checks: 3 },
    });

    renderTab();

    expect(
      await screen.findByText(/3 authored items are inactive/i),
    ).toBeInTheDocument();
  });

  it("shows the server's message when saving fails", async () => {
    server.use(
      http.get(TOOLS_URL, () =>
        HttpResponse.json({ enabled_tools: [], auto_enabled: [], inert_data: {} }),
      ),
      http.put(TOOLS_URL, () =>
        HttpResponse.json({ detail: "Tools are only available in master mode" }, { status: 422 }),
      ),
    );
    const user = userEvent.setup();
    renderTab();

    await user.click(await screen.findByRole("switch", { name: /composure/i }));

    expect(
      await screen.findByText(/only available in master mode/i),
    ).toBeInTheDocument();
  });
});
