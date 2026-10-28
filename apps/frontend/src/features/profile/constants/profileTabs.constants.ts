export type ProfileTabId =
  | "overview"
  | "creations"
  | "campaigns"
  | "endings"
  | "achievements"
  | "bookmarks"
  | "reviews";

export interface ProfileTabDefinition {
  id: ProfileTabId;
  label: string;
  isOwnerOnly: boolean;
}

export const PROFILE_TABS: readonly ProfileTabDefinition[] = [
  { id: "overview", label: "Overview", isOwnerOnly: true },
  { id: "creations", label: "Creations", isOwnerOnly: false },
  { id: "campaigns", label: "Campaigns", isOwnerOnly: true },
  { id: "endings", label: "Endings", isOwnerOnly: true },
  { id: "achievements", label: "Achievements", isOwnerOnly: false },
  { id: "bookmarks", label: "Bookmarks", isOwnerOnly: true },
  { id: "reviews", label: "Reviews", isOwnerOnly: false },
];
