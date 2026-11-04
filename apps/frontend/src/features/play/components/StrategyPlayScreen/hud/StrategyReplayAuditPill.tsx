import React, { useRef, useState } from "react";
import {
  verifyPlaythroughReplay,
  type ReplayVerificationResponse,
} from "../../../api/simulation.api";
import type { StrategyReplayAuditPillProps } from "./StrategyReplayAuditPill.types";
import { IconAlertTriangle, IconCheck, IconShield } from "@tabler/icons-react";

type AuditStatus = "idle" | "verifying" | "verified" | "error";

export const StrategyReplayAuditPill: React.FC<StrategyReplayAuditPillProps> = ({
  playthroughId,
  throughTurn,
  onVerified,
}) => {
  const [rawStatus, setStatus] = useState<AuditStatus>("idle");
  const [result, setResult] = useState<ReplayVerificationResponse | null>(null);
  const [verifiedKey, setVerifiedKey] = useState<string | null>(null);
  const currentKey = `${playthroughId ?? ""}:${throughTurn}`;
  const currentKeyRef = useRef(currentKey);
  currentKeyRef.current = currentKey;
  const isCurrent = verifiedKey === currentKey;
  const status: AuditStatus = rawStatus === "verifying" || isCurrent ? rawStatus : "idle";
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  const handleVerify = async (e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    if (!playthroughId || status === "verifying") return;

    const requestKey = currentKey;
    setVerifiedKey(requestKey);
    setStatus("verifying");
    setIsPopoverOpen(false);
    try {
      const data = await verifyPlaythroughReplay(playthroughId, throughTurn);
      if (currentKeyRef.current !== requestKey) return;
      setResult(data);
      setStatus("verified");
      onVerified?.(data);
    } catch {
      if (currentKeyRef.current === requestKey) setStatus("error");
    }
  };

  const isDisabled = !playthroughId;

  return (
    <div className="relative inline-flex items-center">
      {status === "idle" && (
        <button
          type="button"
          onClick={handleVerify}
          disabled={isDisabled}
          title={
            isDisabled
              ? "Replay verification unavailable in preview mode"
              : "Reconstruct engine state mathematically from turn 0 without LLMs"
          }
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border transition ${
            isDisabled
              ? "bg-[#EAE0D0]/50 text-[#72787C] border-[#3A3128]/10 cursor-not-allowed"
              : "bg-[#F7F0DC]/90 text-[#3A3128] border-[#3A3128]/20 hover:bg-[#FAF0E6] shadow-sm hover:border-[#3A3128]/40"
          }`}
        >
          <IconShield size={12} aria-hidden="true" />
          <span>
            {result && !isCurrent ? `Verify Turn ${throughTurn} (last: Turn ${result.verified_turn})` : "Verify Replay"}
          </span>
        </button>
      )}

      {status === "verifying" && (
        <div
          role="status"
          aria-live="polite"
          className="flex items-center gap-1.5 px-3 py-1 bg-[#F7F0DC]/90 text-[#46606E] border border-[#46606E]/30 rounded-full text-xs font-bold shadow-sm"
        >
          <span className="w-2 h-2 rounded-full bg-[#46606E] animate-ping" />
          <span>Verifying...</span>
        </div>
      )}

      {status === "verified" && result && (
        <div className="relative">
          <button
            type="button"
            onClick={() => setIsPopoverOpen((prev) => !prev)}
            className="flex items-center gap-1.5 px-3 py-1 bg-[#EAF2E8] text-[#3B6638] border border-[#5E8A5A]/40 rounded-full text-xs font-bold hover:bg-[#DEF0DC] transition shadow-sm"
          >
            <span className="w-2 h-2 rounded-full bg-[#5E8A5A]" />
            <span className="inline-flex items-center gap-1"><IconCheck size={12} aria-hidden="true" />History verified</span>
            <span className="text-[10px] font-mono text-[#5E8A5A] opacity-80">
              Turn {result.verified_turn} · {result.world_hash.slice(0, 6)}
            </span>
          </button>

          {isPopoverOpen && (
            <div
              className="absolute right-0 top-full mt-2 w-80 p-3 bg-[#FAF0E6] text-[#221A12] border border-[#3A3128]/20 rounded-xl shadow-xl z-50 flex flex-col gap-2 font-sans"
              role="dialog"
              aria-label="Replay audit details"
            >
              <div className="flex items-center justify-between border-b border-[#3A3128]/10 pb-1.5">
                <span className="text-xs font-bold text-[#3B6638] flex items-center gap-1">
                  <IconCheck size={12} aria-hidden="true" className="inline" /> Mathematical Replay Verification
                </span>
                <button
                  type="button"
                  onClick={() => setIsPopoverOpen(false)}
                  className="text-xs text-[#72787C] hover:text-[#221A12] px-1"
                >
                  ✕
                </button>
              </div>

              <div className="text-[11px] text-[#554A40] flex flex-col gap-1 leading-relaxed">
                <div>
                  <span className="font-semibold text-[#221A12]">Status:</span> All{" "}
                  <span className="font-semibold">{result.step_count} journal steps</span> replayed identically from turn 0 without model calls.
                </div>
                <div>
                  <span className="font-semibold text-[#221A12]">Target Turn:</span> Turn {result.verified_turn}
                </div>
                <div className="flex flex-col gap-0.5 mt-1">
                  <span className="font-semibold text-[#221A12]">State Hash:</span>
                  <div className="font-mono text-[9px] break-all bg-[#F0E4D4] p-1.5 rounded border border-[#3A3128]/10 text-[#46606E]">
                    {result.world_hash}
                  </div>
                </div>
              </div>

              <div className="pt-1.5 border-t border-[#3A3128]/10 flex justify-between items-center">
                <span className="text-[10px] text-[#72787C] italic">
                  Deterministic engine verification
                </span>
                <button
                  type="button"
                  onClick={(e) => handleVerify(e)}
                  className="text-[10px] font-bold text-[#46606E] hover:underline"
                >
                  Re-verify
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {status === "error" && (
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleVerify}
            className="flex items-center gap-1.5 px-3 py-1 bg-[#FBEAE8] text-[#A8483E] border border-[#A8483E]/40 rounded-full text-xs font-bold hover:bg-[#F7D8D4] transition shadow-sm"
          >
            <IconAlertTriangle size={12} aria-hidden="true" />
            <span>Verification Failed</span>
            <span className="text-[10px] underline ml-0.5">Retry</span>
          </button>
        </div>
      )}
    </div>
  );
};
