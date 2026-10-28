import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SanityText } from "./SanityText";

describe("SanityText", () => {
  it("wraps only the picked words and keeps all the text", () => {
    const { container } = render(
      <SanityText
        text="the quiet hallway waits"
        offset={0}
        distortedWords={[{ index: 1, start: 4, end: 9 }]}
      />,
    );

    expect(container.textContent).toBe("the quiet hallway waits");
    const eerie = container.querySelectorAll(".font-eerie");
    expect(eerie).toHaveLength(1);
    expect(eerie[0]).toHaveTextContent("quiet");
  });

  it("maps paragraph offsets into a later segment", () => {
    const { container } = render(
      <SanityText
        text=" and then silence"
        offset={20}
        distortedWords={[
          { index: 0, start: 2, end: 6 },
          { index: 5, start: 30, end: 37 },
        ]}
      />,
    );

    expect(container.textContent).toBe(" and then silence");
    expect(container.querySelector(".font-eerie")).toHaveTextContent("silence");
  });

  it("renders plain text when no word is picked", () => {
    const { container } = render(
      <SanityText text="nothing odd" offset={0} distortedWords={[]} />,
    );

    expect(container.textContent).toBe("nothing odd");
    expect(container.querySelector(".font-eerie")).toBeNull();
  });
});
