import React from "react";
import { createRoot } from "react-dom/client";
import { AnimatedPortrait } from "@/shared/components/AnimatedPortrait/AnimatedPortrait";

const AVATARS = ["mira", "hana", "aldric", "isolde"];
const ROWS = [
  { expression: "neutral", speaking: false },
  { expression: "smile", speaking: false },
  { expression: "angry", speaking: false },
  { expression: "surprise", speaking: false },
  { expression: "neutral", speaking: true },
] as const;

const ROW_INDEX = Number(new URLSearchParams(window.location.search).get("row") ?? 0);

function Harness() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 200px)", gap: 6, padding: 6 }}>
      {[ROWS[ROW_INDEX]].flatMap((row) =>
        AVATARS.map((slug) => (
          <div key={`${slug}-${row.expression}-${row.speaking}`} style={{ width: 200, height: 230, overflow: "hidden", background: "#333" }}>
            <AnimatedPortrait
              avatarUrl={`http://localhost:8000/uploads/premade-avatars/${slug}.mavatar`}
              fallbackSrc="data:image/svg+xml;utf8,<svg></svg>"
              label={slug}
              expression={row.expression}
              isSpeaking={row.speaking}
            />
          </div>
        )),
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<Harness />);
