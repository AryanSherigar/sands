import { describe, expect, it } from "vitest";
import { TransformComponent, TransformWrapper } from "react-zoom-pan-pinch";
import styles from "../StrategyPlayScreen.module.css";

describe("StrategyPlayScreen styles and dependencies", () => {
  it("exports expected css class names", () => {
    expect(styles).toBeDefined();
    expect(styles.inkBorder).toBeDefined();
    expect(styles.inkBorderLight).toBeDefined();
    expect(styles.inkShadow).toBeDefined();
    expect(styles.inkShadowLg).toBeDefined();
    expect(styles.verticalWritingMode).toBeDefined();
    expect(styles.parchmentPanel).toBeDefined();
  });

  it("exports react-zoom-pan-pinch components", () => {
    expect(TransformWrapper).toBeDefined();
    expect(TransformComponent).toBeDefined();
  });
});
