import { RATING_VALUES } from "@/shared/constants/alpha-survey";
import type { RatingRowProps } from "./RatingRow.types";

export function RatingRow({ label, value, onChange }: RatingRowProps) {
  return (
    <div role="radiogroup" aria-label={label} className="space-y-2">
      <p className="text-sm text-content">{label}</p>
      <div className="flex gap-2">
        {RATING_VALUES.map((rating) => {
          const isSelected = value === rating;
          return (
            <button
              key={rating}
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => onChange(rating)}
              className={`min-h-11 min-w-11 rounded-md border font-mono text-sm transition-colors cursor-pointer ${
                isSelected
                  ? "border-primary bg-primary text-primary-contrast"
                  : "border-border-strong bg-surface-raised text-content hover:bg-surface-overlay"
              }`}
            >
              {rating}
            </button>
          );
        })}
      </div>
    </div>
  );
}
