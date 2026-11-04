import { CHRONICLERS } from "../../constants/chroniclers";
import type { ChroniclerPickerProps } from "./ChroniclerPicker.types";

export const ChroniclerPicker = ({ selectedId, onSelect }: ChroniclerPickerProps) => {
  const handleSelect = (id: string) => () => onSelect(id);

  return (
    <section className="mb-6 rounded-xl border border-[#3A3128]/20 bg-[#F3EAD3] p-4 shadow-sm">
      <h2 className="text-lg font-bold text-[#3A3128] font-['EB_Garamond',serif]">
        Your Chronicler
      </h2>
      <p className="mb-3 text-xs italic text-[#72787C]">
        Your chronicler is chosen once and writes your whole story.
      </p>
      <div role="radiogroup" aria-label="Chronicler" className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {CHRONICLERS.map((chronicler) => {
          const isSelected = chronicler.id === selectedId;
          const AvatarIcon = chronicler.avatarIcon;
          return (
            <button
              key={chronicler.id}
              type="button"
              role="radio"
              aria-checked={isSelected}
              aria-label={`${chronicler.name}, ${chronicler.title}`}
              onClick={handleSelect(chronicler.id)}
              className={`rounded-lg border p-3 text-left transition ${
                isSelected
                  ? "border-[#D2A94A] bg-[#EFE4C8] ring-2 ring-[#D2A94A]/50"
                  : "border-[#3A3128]/15 bg-transparent hover:bg-[#EFE4C8]/60"
              }`}
            >
              <span className="block text-sm font-semibold text-[#3A3128]">
                <AvatarIcon size={14} aria-hidden="true" className="mr-1 inline" />
                {chronicler.name}
              </span>
              <span className="block text-xs uppercase tracking-wide text-[#72787C]">
                {chronicler.title}
              </span>
              <span className="mt-1 block text-xs text-[#3A3128]/80">{chronicler.tagline}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
};
