import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { ALPHA_CONSENT_VERSION } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import { ALPHA_CONSENT_COPY } from "../../../constants/alpha-consent";
import { AlphaReconsent } from "../AlphaReconsent";

describe("AlphaReconsent", () => {
  it("shows the consent copy and sends the accepted version", async () => {
    let sentBody: unknown = null;
    server.use(
      http.post("*/v1/users/me/alpha-consent", async ({ request }) => {
        sentBody = await request.json();
        return HttpResponse.json({ alpha_consent_is_current: true });
      }),
    );
    render(<AlphaReconsent version={ALPHA_CONSENT_VERSION} />, {
      wrapper: createQueryWrapper(),
    });

    expect(
      screen.getByText(ALPHA_CONSENT_COPY[ALPHA_CONSENT_VERSION].title),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /i accept/i }));

    await screen.findByRole("button", { name: /i accept/i });
    expect(sentBody).toEqual({ version: ALPHA_CONSENT_VERSION });
  });

  it("tells the player when saving the consent fails", async () => {
    server.use(
      http.post(
        "*/v1/users/me/alpha-consent",
        () => new HttpResponse(null, { status: 500 }),
      ),
    );
    render(<AlphaReconsent version={ALPHA_CONSENT_VERSION} />, {
      wrapper: createQueryWrapper(),
    });

    await userEvent.click(screen.getByRole("button", { name: /i accept/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/try again/i);
  });
});
