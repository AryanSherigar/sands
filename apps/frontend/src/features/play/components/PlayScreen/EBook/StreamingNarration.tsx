import { ReactElement, useEffect } from "react";
import { READER_FONT_SIZE_CLASSES } from "@/shared/constants/reader-preferences";
import { usePlayStore } from "../../../stores/play.store";
import { DistortedStreamingText } from "./DistortedStreamingText";
import { StreamingNarrationProps } from "./StreamingNarration.types";

function renderStreamingHeader(
  chapterNumber: number,
  onStop: () => void,
): ReactElement {
  return (
    <header className="flex items-center justify-between font-mono text-xs opacity-60 mb-4 tracking-wider">
      <span className="uppercase flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-accent animate-ping" />
        Inscribing Chapter {chapterNumber}...
      </span>
      <button
        type="button"
        onClick={onStop}
        className="px-2.5 py-1 rounded-md border border-border-strong bg-surface-raised text-content-muted hover:text-content cursor-pointer font-mono text-[10px]"
      >
        Stop
      </button>
    </header>
  );
}

function renderStreamingAction(
  characterName: string,
  mode: string,
  action: string,
): ReactElement | null {
  if (!action || action === "Continue the story.") return null;
  return (
    <aside className="mb-5 pl-4 border-l-2 border-border-strong italic font-serif text-sm opacity-80">
      <span className="font-mono text-xs not-italic opacity-70 mr-1.5 uppercase font-medium">
        {characterName} ({mode}):
      </span>
      "{action}"
    </aside>
  );
}

function renderStreamingBody(
  text: string,
  props: StreamingNarrationProps,
): ReactElement {
  if (!text) {
    return (
      <p className="italic opacity-50 text-sm">
        The narrator considers your choices...
      </p>
    );
  }
  if (props.shouldDistort) {
    return (
      <DistortedStreamingText
        text={text}
        fontClass={props.fontClass}
        turnNumber={props.chapterNumber}
        playthroughId={props.playthroughId}
      />
    );
  }
  return (
    <p>
      {text}
      <span className="inline-block w-0.5 h-4 ml-1 bg-accent animate-pulse align-middle" />
    </p>
  );
}

export function StreamingNarration(props: StreamingNarrationProps): ReactElement {
  const streamingText = usePlayStore((state) => state.streaming_text);
  const lastAction = usePlayStore((state) => state.last_submitted_action);
  const activeMode = usePlayStore((state) => state.active_mode);
  const stopGeneration = usePlayStore((state) => state.stopGeneration);
  const readerFontSize = usePlayStore((state) => state.reader_font_size);
  const { onScrollToBottom } = props;

  useEffect(() => {
    onScrollToBottom("auto");
  }, [streamingText, onScrollToBottom]);

  return (
    <section className="my-8 pt-6 border-t border-inherit/20 animate-fade-in">
      {renderStreamingHeader(props.chapterNumber, stopGeneration)}
      {renderStreamingAction(props.characterName, activeMode, lastAction)}
      <div
        className={`${props.fontClass} ${READER_FONT_SIZE_CLASSES[readerFontSize]} leading-relaxed space-y-4`}
      >
        {renderStreamingBody(streamingText, props)}
      </div>
    </section>
  );
}
