import { KeyboardEvent, useEffect, useRef, useState } from "react";
import {
  IconEye,
  IconEyeOff,
  IconFeather,
  IconMicrophone,
  IconSparkles,
  IconSwords,
  IconWriting,
} from "@tabler/icons-react";
import type { FantasyComposerProps, FantasyModeKey } from "./FantasyComposer.types";

function ModePills({
  activeMode,
  onSelectMode,
  canRetry,
  onRetry,
}: {
  activeMode: FantasyModeKey;
  onSelectMode: (mode: FantasyModeKey) => void;
  canRetry: boolean;
  onRetry: () => void;
}) {
  return (
    <div className="flex items-center justify-between mb-3 border-b border-[#2E2419] pb-2.5">
      <div className="flex items-center gap-1.5 bg-[#0E0B08] p-1 rounded-md border border-[#2E2419]">
        <button
          type="button"
          onClick={() => onSelectMode("do")}
          className={`px-3 py-1 rounded text-label-ui font-serif flex items-center gap-1.5 tracking-wide transition-all shadow-sm ${
            activeMode === "do"
              ? "text-[#F2DCA2] bg-[#C5A059]/20 border border-[#C5A059]/50 font-semibold"
              : "text-[#A89F91] hover:text-[#EDE0CA] hover:bg-[#1E1812]"
          }`}
        >
          <IconSwords size={15} className="text-[#C5A059]" />
          <span>Deed (Do)</span>
        </button>
        <button
          type="button"
          onClick={() => onSelectMode("say")}
          className={`px-3 py-1 rounded text-label-ui font-serif flex items-center gap-1.5 tracking-wide transition-all shadow-sm ${
            activeMode === "say"
              ? "text-[#F2DCA2] bg-[#C5A059]/20 border border-[#C5A059]/50 font-semibold"
              : "text-[#A89F91] hover:text-[#EDE0CA] hover:bg-[#1E1812]"
          }`}
        >
          <IconMicrophone size={15} className="text-[#C5A059]" />
          <span>Utter (Say)</span>
        </button>
        <button
          type="button"
          onClick={() => onSelectMode("cast")}
          className={`px-3 py-1 rounded text-label-ui font-serif flex items-center gap-1.5 tracking-wide transition-all shadow-sm ${
            activeMode === "cast"
              ? "text-[#F2DCA2] bg-[#C5A059]/20 border border-[#C5A059]/50 font-semibold"
              : "text-[#CDB083] hover:text-[#EDE0CA] hover:bg-[#1E1812]"
          }`}
        >
          <IconSparkles size={15} className="text-[#C5A059]" />
          <span>Incant (Cast)</span>
        </button>
      </div>
      <div className="flex items-center gap-2">
        {canRetry && (
          <button type="button" onClick={onRetry} className="text-[#C5A059] hover:underline font-mono text-[11px]">
            ↺ Retry Turn
          </button>
        )}
        <span className="font-mono text-[11px] text-[#8C7A6B] hidden sm:flex items-center gap-1.5">
          <IconWriting size={13} className="text-[#C5A059]" />
          <span>Scribe Desk · Codex Engine</span>
        </span>
      </div>
    </div>
  );
}

function InclinationChips({
  chips,
  show,
  onToggleShow,
  onSelectChip,
}: {
  chips: string[];
  show: boolean;
  onToggleShow: () => void;
  onSelectChip: (text: string) => void;
}) {
  if (chips.length === 0) return null;

  return (
    <div className="mb-3.5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-serif text-[#A49079] uppercase tracking-wider flex items-center gap-1">
          <span className="text-[#C5A059] text-[10px]">❧</span> Tactical Inclinations
        </span>
        <button
          type="button"
          onClick={onToggleShow}
          className="flex items-center gap-1 text-[11px] font-serif text-[#8C7A6B] hover:text-[#EDE0CA] bg-[#1A1612] hover:bg-[#221C16] px-2 py-0.5 rounded border border-[#3E3224] transition-colors cursor-pointer"
        >
          {show ? <IconEyeOff size={13} className="text-[#C5A059]" /> : <IconEye size={13} className="text-[#C5A059]" />}
          <span>{show ? "Hide" : "Show"}</span>
        </button>
      </div>
      {show && (
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar whitespace-nowrap pb-1">
          {chips.map((chip, idx) => (
            <button
              key={`${chip}-${idx}`}
              type="button"
              onClick={() => onSelectChip(chip)}
              className="shrink-0 px-2.5 py-1 rounded bg-[#1B1510] hover:bg-[#261E16] border border-[#3E3224] hover:border-[#C5A059]/60 text-[#EDE0CA] text-[12px] font-serif transition-colors text-left flex items-center gap-1.5 shadow-sm group cursor-pointer"
            >
              <span className="text-[#C5A059] group-hover:scale-105 transition-transform">✦</span>
              <span>"{chip}"</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ComposerFooter({
  isNarrating,
  onContinue,
}: {
  isNarrating: boolean;
  onContinue: () => void;
}) {
  return (
    <div className="flex items-center justify-between pt-1">
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={isNarrating}
          onClick={onContinue}
          className="text-[#8C7A6B] hover:text-[#EDE0CA] font-serif text-[13px] transition-colors underline-offset-4 hover:underline disabled:opacity-40"
        >
          Advance turn without proclamation
        </button>
        <span className="text-[#382E25]">·</span>
        <span className="font-mono text-[10px] text-[#8C7A6B] hidden sm:inline">⌘ + Enter to seal deed</span>
      </div>
      <button
        type="submit"
        disabled={isNarrating}
        className="flex items-center gap-2 px-5 h-10 rounded-md bg-[#C5A059] hover:bg-[#D4AF37] text-[#14110E] font-serif font-bold active:scale-[0.98] transition-all text-[15px] shadow-lg tracking-wide disabled:opacity-40 cursor-pointer"
      >
        <IconWriting size={17} />
        <span>Seal & Inscribe</span>
        <IconFeather size={17} />
      </button>
    </div>
  );
}

export function FantasyComposer({
  tacticalInclinations,
  isNarrating,
  canRetry,
  draftInsertion,
  onSubmit,
  onContinue,
  onRetry,
}: FantasyComposerProps) {
  const [text, setText] = useState("");
  const [activeMode, setActiveMode] = useState<FantasyModeKey>("do");
  const [showChips, setShowChips] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lastDraftId = useRef<number | null>(null);

  useEffect(() => {
    if (!draftInsertion || lastDraftId.current === draftInsertion.requestId) return;
    lastDraftId.current = draftInsertion.requestId;
    setActiveMode("say");
    setText(draftInsertion.text);
    textareaRef.current?.focus();
  }, [draftInsertion]);

function getActionPrefix(mode: FantasyModeKey): string {
  if (mode === "say") return 'I say: "';
  if (mode === "cast") return "I cast: ";
  return "";
}

  const handleSubmit = (event?: React.FormEvent) => {
    event?.preventDefault();
    if (isNarrating || !text.trim()) return;
    const prefix = getActionPrefix(activeMode);
    const suffix = activeMode === "say" ? '"' : "";
    onSubmit(`${prefix}${text.trim()}${suffix}`);
    setText("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSelectChip = (chipText: string) => {
    setText(chipText);
    textareaRef.current?.focus();
  };

  return (
    <section aria-label="Tactile Scribe Desk" className="mt-8 rounded-xl bg-[#14100C] border border-[#3E3224] p-4 shadow-2xl relative w-full max-w-[720px]">
      <ModePills activeMode={activeMode} onSelectMode={setActiveMode} canRetry={canRetry} onRetry={onRetry} />
      <InclinationChips chips={tacticalInclinations} show={showChips} onToggleShow={() => setShowChips(!showChips)} onSelectChip={handleSelectChip} />
      <form className="space-y-3" onSubmit={handleSubmit}>
        <div className="relative rounded-lg bg-[#0F0C09] border border-[#3E3224] focus-within:border-[#C5A059] transition-colors">
          <label className="sr-only" htmlFor="action-composer">Inscribe your intent</label>
          <textarea
            id="action-composer"
            ref={textareaRef}
            rows={3}
            value={text}
            disabled={isNarrating}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Inscribe your intent onto the chronicle parchment..."
            className="w-full bg-transparent p-3.5 font-serif text-[17px] text-[#F5EEDB] placeholder-[#8C7A6B] focus:outline-none resize-none leading-relaxed min-h-[90px]"
          />
          <div className="flex items-center justify-between px-3 py-1.5 border-t border-[#261D15] font-mono text-[#8C7A6B] text-[10px]">
            <span className="flex items-center gap-1 text-[#A89885]">
              <IconWriting size={12} className="text-[#C5A059]" />
              PARCHMENT REGISTER · TACTILE SCRIPT
            </span>
            <span>ESC to clear draft</span>
          </div>
        </div>
        <ComposerFooter isNarrating={isNarrating} onContinue={onContinue} />
      </form>
    </section>
  );
}
