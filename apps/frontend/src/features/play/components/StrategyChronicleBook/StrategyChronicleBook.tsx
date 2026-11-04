import { useEffect, useRef } from "react";
import { getChronicler } from "../../constants/chroniclers";
import { useStrategyChronicleBook } from "../../hooks/useStrategyChronicleBook";
import { useStrategyEpilogue } from "../../hooks/useStrategyEpilogue";
import { bookFileName, composeBookText } from "../../lib/bookExport";
import { BookChapter } from "./BookChapter";
import { BookClosingEntry } from "./BookClosingEntry";
import { BookCover } from "./BookCover";
import { BookShareActions } from "./BookShareActions";
import { BOOK_PREPARING_MESSAGE } from "./strategyBook.constants";
import type { StrategyChronicleBookProps } from "./StrategyChronicleBook.types";

export const StrategyChronicleBook = ({
  playthroughId,
  rulerName,
  chroniclerId,
  eraLabel,
  onClose,
}: StrategyChronicleBookProps) => {
  const book = useStrategyChronicleBook(playthroughId);
  const epilogue = useStrategyEpilogue(playthroughId);
  const chronicler = getChronicler(chroniclerId);
  const hasStartedClosingEntry = useRef(false);
  const { isPreparing } = book;
  const { status, start } = epilogue;
  const isComplete = !isPreparing && status === "completed";
  const bookText = composeBookText({
    rulerName,
    chroniclerName: chronicler.name,
    chroniclerTitle: chronicler.title,
    eraLabel,
    chapters: book.chapters.map((chapter) => chapter.narration),
    closingEntry: epilogue.narration,
  });

  useEffect(() => {
    if (isPreparing || status !== "pending" || hasStartedClosingEntry.current) return;
    hasStartedClosingEntry.current = true;
    start();
  }, [isPreparing, status, start]);

  return (
    <div className="absolute inset-0 z-50 overflow-y-auto bg-[#3A3128]/70 p-4 sm:p-8">
      <article className="mx-auto max-w-2xl rounded-xl border border-[#D2A94A]/60 bg-[#F3EAD3] p-8 shadow-2xl">
        <BookCover
          rulerName={rulerName}
          chroniclerName={chronicler.name}
          chroniclerTitle={chronicler.title}
          eraLabel={eraLabel}
        />
        {book.chapters.map((chapter, index) => (
          <BookChapter key={chapter.summaryId} ordinal={index + 1} narration={chapter.narration} />
        ))}
        {isPreparing ? (
          <p className="py-6 text-center text-sm italic text-[#72787C]" aria-live="polite">
            {BOOK_PREPARING_MESSAGE}
          </p>
        ) : (
          <BookClosingEntry
            narration={epilogue.narration}
            status={status}
            errorMessage={epilogue.errorMessage}
            onRetry={start}
          />
        )}
        {isComplete ? <BookShareActions text={bookText} fileName={bookFileName(rulerName)} /> : null}
        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md bg-[#46606E] px-5 py-2 text-white hover:bg-[#354F5A] focus-visible:outline focus-visible:outline-2"
          >
            Close the book
          </button>
        </div>
      </article>
    </div>
  );
};
