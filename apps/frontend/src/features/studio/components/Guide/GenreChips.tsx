import React from "react";
import { GENRES } from "@/shared/constants/genres";
import { PRIMARY_GENRE_LABEL } from "../../constants/guideChips";
import { useGuide } from "../../hooks/useGuide";
import { useSyncedValue } from "../../hooks/useSyncedValue";
import { toggleTag } from "../../lib/guideTags";
import { GuideChip } from "./GuideChip";

const EMPTY_TAGS: string[] = [];

export const GenreChips: React.FC = () => {
  const { scenario, saveFields } = useGuide();
  const { value: selected, commit } = useSyncedValue(
    scenario?.genre_tags ?? EMPTY_TAGS,
    (next) => saveFields({ genre_tags: next }),
  );

  return (
    <div role="group" aria-labelledby="genre-chips-label" className="space-y-2">
      <p id="genre-chips-label" className="text-meta font-medium text-content-muted">
        What kind of story is it?
      </p>
      <div className="flex flex-wrap gap-2">
        {GENRES.map((genre) => (
          <GuideChip
            key={genre}
            label={genre}
            isSelected={selected.includes(genre)}
            badge={selected[0] === genre ? PRIMARY_GENRE_LABEL : undefined}
            onClick={() => commit(toggleTag(selected, genre))}
          />
        ))}
      </div>
    </div>
  );
};
