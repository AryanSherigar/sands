import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { fetchSfxFile, SfxPlayer } from "../sfx-player";
import { FakeAudioBuffer, FakeAudioContext } from "./fakeAudioContext";

const makeContext = (
  decode: (bytes: ArrayBuffer) => Promise<AudioBuffer>,
): BaseAudioContext => {
  const context = new FakeAudioContext() as unknown as BaseAudioContext & {
    decodeAudioData: typeof decode;
  };
  context.decodeAudioData = decode;
  return context;
};

const recording = new FakeAudioBuffer(1, 10, 8000) as unknown as AudioBuffer;
const peak = (buffer: AudioBuffer): number =>
  buffer.getChannelData(0).reduce((max, sample) => Math.max(max, Math.abs(sample)), 0);

describe("SfxPlayer", () => {
  it("prefers a recorded file when one exists", async () => {
    const loadFile = vi.fn().mockResolvedValue(new ArrayBuffer(8));
    const player = new SfxPlayer(makeContext(async () => recording), loadFile);

    const buffer = await player.getBuffer("heavy_knock");

    expect(buffer).toBe(recording);
    expect(loadFile).toHaveBeenCalledWith("/audio/sfx/heavy_knock.mp3");
  });

  it("falls back to synthesis when the file is missing", async () => {
    const player = new SfxPlayer(
      makeContext(async () => recording),
      async () => null,
    );

    const buffer = await player.getBuffer("heavy_knock");

    expect(buffer).not.toBe(recording);
    expect(peak(buffer)).toBeGreaterThan(0.05);
  });

  it("falls back when the file cannot be decoded (a corrupt file or an HTML shell)", async () => {
    const player = new SfxPlayer(
      makeContext(async () => {
        throw new Error("EncodingError");
      }),
      async () => new ArrayBuffer(4),
    );

    const buffer = await player.getBuffer("light_buzz");

    expect(peak(buffer)).toBeGreaterThan(0.05);
  });

  it("falls back when loading the file throws", async () => {
    const player = new SfxPlayer(makeContext(async () => recording), async () => {
      throw new TypeError("network down");
    });

    expect(peak(await player.getBuffer("radio_static"))).toBeGreaterThan(0.05);
  });

  it("falls back when the context cannot decode at all", async () => {
    const context = new FakeAudioContext() as unknown as BaseAudioContext;
    const player = new SfxPlayer(context, async () => new ArrayBuffer(4));

    expect(peak(await player.getBuffer("lamp_click"))).toBeGreaterThan(0.05);
  });

  it("asks for each cue's file only once and remembers the answer", async () => {
    const loadFile = vi.fn().mockResolvedValue(null);
    const player = new SfxPlayer(makeContext(async () => recording), loadFile);

    const first = await player.getBuffer("elevator_chime");
    const second = await player.getBuffer("elevator_chime");

    expect(second).toBe(first);
    expect(loadFile).toHaveBeenCalledTimes(1);
  });

  it("preloads several cues without waiting", async () => {
    const loadFile = vi.fn().mockResolvedValue(null);
    const player = new SfxPlayer(makeContext(async () => recording), loadFile);

    player.preload(["phone_ring", "heavy_knock"]);
    await player.getBuffer("phone_ring");

    expect(loadFile).toHaveBeenCalledTimes(2);
  });
});

describe("fetchSfxFile", () => {
  it("returns the bytes of a real audio file", async () => {
    server.use(
      http.get("*/audio/sfx/phone_ring.mp3", () =>
        HttpResponse.arrayBuffer(new ArrayBuffer(6), {
          headers: { "content-type": "audio/mpeg" },
        }),
      ),
    );

    const bytes = await fetchSfxFile("/audio/sfx/phone_ring.mp3");

    expect(bytes?.byteLength).toBe(6);
  });

  it("treats a 404 as no file", async () => {
    server.use(
      http.get("*/audio/sfx/phone_ring.mp3", () => new HttpResponse(null, { status: 404 })),
    );

    expect(await fetchSfxFile("/audio/sfx/phone_ring.mp3")).toBeNull();
  });

  it("treats an HTML shell answered with 200 as no file", async () => {
    server.use(
      http.get("*/audio/sfx/phone_ring.mp3", () =>
        HttpResponse.html("<!doctype html><html></html>"),
      ),
    );

    expect(await fetchSfxFile("/audio/sfx/phone_ring.mp3")).toBeNull();
  });
});
