import type { BookCoverProps } from "./BookCover.types";

export const BookCover = ({ rulerName, chroniclerName, chroniclerTitle, eraLabel }: BookCoverProps) => (
  <header className="border-b border-[#3A3128]/20 pb-8 text-center">
    <p className="text-xs font-semibold uppercase tracking-widest text-[#72787C]">
      The Chronicle of
    </p>
    <h1 className="mt-3 font-['EB_Garamond',serif] text-4xl font-bold text-[#3A3128]">
      {rulerName}
    </h1>
    <p className="mt-2 font-serif text-base italic text-[#554A40]">{eraLabel}</p>
    <p className="mt-6 text-sm text-[#72787C]">
      Set down by {chroniclerName}, {chroniclerTitle}
    </p>
  </header>
);
