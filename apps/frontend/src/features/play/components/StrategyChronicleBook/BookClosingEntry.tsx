import { BOOK_RETRY_LABEL } from "./strategyBook.constants";
import type { BookClosingEntryProps } from "./BookClosingEntry.types";

export const BookClosingEntry = ({ narration, status, errorMessage, onRetry }: BookClosingEntryProps) => {
  if (status === "failed") {
    return (
      <section className="border-t border-[#3A3128]/20 py-8 text-center" role="alert">
        <p className="text-sm text-[#72787C]">{errorMessage}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-[#3A3128]/30 px-4 py-2 text-sm font-semibold text-[#3A3128] hover:bg-[#EFE4C8]"
        >
          {BOOK_RETRY_LABEL}
        </button>
      </section>
    );
  }
  if (!narration) return null;
  return (
    <section className="border-t border-[#3A3128]/20 py-8" aria-live="polite">
      <p className="whitespace-pre-wrap font-serif text-lg italic leading-relaxed text-[#3A3128]">
        {narration}
      </p>
    </section>
  );
};
