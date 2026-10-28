import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import {
  ALPHA_CONFIG,
  ALPHA_CONSENT_VERSION,
  NON_ALPHA_CONFIG,
  alphaConfigHandler,
} from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_CONSENT_COPY } from "../../../constants/alpha-consent";
import { AlphaConsent } from "../AlphaConsent";

describe("AlphaConsent", () => {
  it("shows the consent copy for the server's version in alpha mode", async () => {
    server.use(alphaConfigHandler(ALPHA_CONFIG));
    render(<AlphaConsent />, { wrapper: createQueryWrapper() });

    const copy = ALPHA_CONSENT_COPY[ALPHA_CONSENT_VERSION];
    expect(await screen.findByText(copy.title)).toBeInTheDocument();
    copy.paragraphs.forEach((paragraph) =>
      expect(screen.getByText(paragraph)).toBeInTheDocument(),
    );
  });

  it("renders nothing when alpha mode is off", async () => {
    server.use(alphaConfigHandler(NON_ALPHA_CONFIG));
    const { container } = render(<AlphaConsent />, {
      wrapper: createQueryWrapper(),
    });

    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(container).toBeEmptyDOMElement();
  });

  it("tells visitors new sign-ups are closed but existing testers can sign in", async () => {
    server.use(
      alphaConfigHandler({ ...ALPHA_CONFIG, is_signup_enabled: false }),
    );
    render(<AlphaConsent />, { wrapper: createQueryWrapper() });

    expect(await screen.findByRole("status")).toHaveTextContent(
      /new sign-ups are closed/i,
    );
  });

  it("falls back to the newest copy for an unknown version", async () => {
    server.use(
      alphaConfigHandler({ ...ALPHA_CONFIG, consent_version: "alpha-99" }),
    );
    render(<AlphaConsent />, { wrapper: createQueryWrapper() });

    expect(
      await screen.findByText(ALPHA_CONSENT_COPY[ALPHA_CONSENT_VERSION].title),
    ).toBeInTheDocument();
  });
});
