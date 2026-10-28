import type { DiscoverLibrary } from "../../types/discover.types";

export interface LibraryFilterProps {
  value: DiscoverLibrary | null;
  isAuthenticated: boolean;
  onChange: (next: DiscoverLibrary | null) => void;
  onSignIn: () => void;
}
