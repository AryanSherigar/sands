import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { ReadingDefaultsSection } from "../ReadingDefaultsSection";

const renderSection = (config: AlphaConfig): void => {
  server.use(
    http.get("*/v1/users/me", () =>
      HttpResponse.json({ voice_output_enabled: false }),
    ),
  );
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <ReadingDefaultsSection />
    </Wrapper>,
  );
};

describe("ReadingDefaultsSection voice switch", () => {
  it("is shown when alpha mode is off", () => {
    renderSection(NON_ALPHA_CONFIG);
    expect(screen.getByText("Voice narration stream")).toBeInTheDocument();
  });

  it("is hidden in alpha mode while the ambience switch stays", () => {
    renderSection(ALPHA_CONFIG);
    expect(screen.queryByText("Voice narration stream")).toBeNull();
    expect(screen.getByText("Background scenario ambience")).toBeInTheDocument();
  });
});
