import { useState } from "react";
import type { BookShareActionsProps } from "./BookShareActions.types";

const BUTTON_CLASS =
  "rounded-md border border-[#46606E] px-4 py-2 text-sm text-[#46606E] hover:bg-[#46606E]/10 focus-visible:outline focus-visible:outline-2";
const COPIED_MESSAGE = "Copied to your clipboard.";
const COPY_FAILED_MESSAGE = "Your browser would not allow copying. Save it as a file instead.";

export const BookShareActions = ({ text, fileName }: BookShareActionsProps) => {
  const [notice, setNotice] = useState<string | null>(null);

  const handleCopy = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      setNotice(COPIED_MESSAGE);
    } catch {
      setNotice(COPY_FAILED_MESSAGE);
    }
  };

  const handleSave = (): void => {
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
      <button type="button" onClick={handleCopy} className={BUTTON_CLASS}>
        Copy the book
      </button>
      <button type="button" onClick={handleSave} className={BUTTON_CLASS}>
        Save as a text file
      </button>
      {notice ? (
        <p className="w-full text-center text-xs text-[#72787C]" role="status">
          {notice}
        </p>
      ) : null}
    </div>
  );
};
