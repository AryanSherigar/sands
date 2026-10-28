import { describe, expect, it } from "vitest";
import { parseClockText } from "./parseClockText";

describe("parseClockText", () => {
  it.each([
    ["11:52 pm", [1432]],
    ["11:52pm", [1432]],
    ["11.52 PM", [1432]],
    ["11 52 p.m.", [1432]],
    ["2352", [1432]],
    ["23:52", [1432]],
    [" 11:52 PM ", [1432]],
    ["11:52", [712, 1432]],
    ["6 am", [360]],
    ["952", [592, 1312]],
    ["0009", [9]],
    ["12:09 am", [9]],
    ["12:09 pm", [729]],
  ])("reads %j as %j", (text, expected) => {
    expect(parseClockText(text)).toEqual(expected);
  });

  it.each([
    "",
    "   ",
    "eleven fifty-two",
    "11:60",
    "25:00",
    "13:00 pm",
    "0:30 am",
    "11:5",
    "11:52:00",
  ])("rejects %j", (text) => {
    expect(parseClockText(text)).toEqual([]);
  });
});
