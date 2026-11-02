import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { StrategyArtSlot } from "../StrategyArtSlot";

const ART_URL = "https://cdn.test/strategy-art/one.webp";

describe("StrategyArtSlot", () => {
  it("requests art for the given kind and item then shows it", async () => {
    const seen = vi.fn();
    server.use(
      http.post("*/trs/v1/strategy/playthroughs/pt-1/art", async ({ request }) => {
        seen(await request.json());
        return HttpResponse.json({
          kind: "uprising",
          item_id: "upr_1",
          status: "completed",
          art_url: ART_URL,
          error_code: null,
          is_retryable: false,
        });
      }),
    );
    const Wrapper = createQueryWrapper();
    render(
      <Wrapper>
        <StrategyArtSlot playthroughId="pt-1" kind="uprising" itemId="upr_1" altText="Riot" />
      </Wrapper>,
    );
    expect(await screen.findByRole("img", { name: "Riot" })).toHaveAttribute("src", ART_URL);
    expect(seen.mock.calls[0][0]).toMatchObject({ kind: "uprising", item_id: "upr_1" });
  });
});
