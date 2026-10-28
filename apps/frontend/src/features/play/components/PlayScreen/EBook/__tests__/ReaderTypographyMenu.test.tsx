import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { usePlayStore } from "../../../../stores/play.store";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import type { PlaythroughData } from "../../../../types/play.types";
import { ReaderTypographyMenu } from "../ReaderTypographyMenu";

describe("ReaderTypographyMenu", () => {
  beforeEach(() => {
    usePlayStore.setState({
      reader_font_override: null,
      playthrough: null,
    });
  });

  it("renders the typography Aa button", () => {
    render(<ReaderTypographyMenu />);
    expect(
      screen.getByRole("button", { name: /typography settings/i }),
    ).toBeInTheDocument();
  });

  it("opens the typography menu and allows selecting an override font", async () => {
    const user = userEvent.setup();
    render(<ReaderTypographyMenu />);

    const button = screen.getByRole("button", { name: /typography settings/i });
    await user.click(button);

    const select = screen.getByLabelText(/reader narration font/i);
    expect(select).toBeInTheDocument();

    await user.selectOptions(select, "special-elite");
    expect(usePlayStore.getState().reader_font_override).toBe("special-elite");

    await user.selectOptions(select, "default");
    expect(usePlayStore.getState().reader_font_override).toBeNull();
  });

  const withTools = (enabledTools: string[]): void => {
    usePlayStore.setState({
      playthrough: { enabled_tools: enabledTools } as PlaythroughData,
    });
  };

  it("offers the effects switch only when a tool with effects is on", async () => {
    const user = userEvent.setup();
    withTools(["rule_checks"]);
    render(<ReaderTypographyMenu />);

    await user.click(screen.getByRole("button", { name: /typography settings/i }));

    expect(
      screen.getByRole("checkbox", { name: /reduce sensory effects/i }),
    ).toBeInTheDocument();
  });

  it("hides the effects switch for a scenario with no tools", async () => {
    const user = userEvent.setup();
    withTools([]);
    render(<ReaderTypographyMenu />);

    await user.click(screen.getByRole("button", { name: /typography settings/i }));

    expect(screen.queryByRole("checkbox", { name: /reduce sensory effects/i })).toBeNull();
  });

  it("toggles the reduce-effects preference", async () => {
    const user = userEvent.setup();
    useReaderPreferencesStore.setState({ reduceSensoryEffects: false });
    withTools(["atmosphere"]);
    render(<ReaderTypographyMenu />);
    await user.click(screen.getByRole("button", { name: /typography settings/i }));

    await user.click(screen.getByRole("checkbox", { name: /reduce sensory effects/i }));

    expect(useReaderPreferencesStore.getState().reduceSensoryEffects).toBe(true);
  });
});
