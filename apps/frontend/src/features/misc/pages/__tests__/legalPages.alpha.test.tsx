import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_DATA_NOTICE } from "@/shared/constants/alpha-data-notice";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { PrivacyPage } from "../PrivacyPage";
import { TermsPage } from "../TermsPage";

const renderPage = (config: AlphaConfig, page: React.ReactElement): void => {
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <MemoryRouter>{page}</MemoryRouter>
    </Wrapper>,
  );
};

describe.each([
  ["TermsPage", <TermsPage key="t" />],
  ["PrivacyPage", <PrivacyPage key="p" />],
])("%s", (_name, page) => {
  it("shows the alpha data notice in alpha mode", () => {
    renderPage(ALPHA_CONFIG, page);
    expect(screen.getByText(ALPHA_DATA_NOTICE)).toBeInTheDocument();
  });

  it("shows no alpha notice when alpha mode is off", () => {
    renderPage(NON_ALPHA_CONFIG, page);
    expect(screen.queryByText(ALPHA_DATA_NOTICE)).toBeNull();
  });
});
