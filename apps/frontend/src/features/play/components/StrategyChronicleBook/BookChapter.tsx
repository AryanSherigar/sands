import type { BookChapterProps } from "./BookChapter.types";

export const BookChapter = ({ ordinal, narration }: BookChapterProps) => (
  <section data-testid="book-chapter" className="py-6">
    <h2 className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#72787C]">
      Chapter {ordinal}
    </h2>
    <p className="whitespace-pre-wrap font-serif text-lg leading-relaxed text-[#3A3128]">
      {narration}
    </p>
  </section>
);
