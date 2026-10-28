export interface MobileFilterBarProps {
  selectedGenres: string[];
  activeFilterCount: number;
  onToggleGenre: (genre: string) => void;
  onOpenFilters: () => void;
}
