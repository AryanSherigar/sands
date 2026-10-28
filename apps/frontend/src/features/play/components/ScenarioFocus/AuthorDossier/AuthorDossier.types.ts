export interface AuthorDossierProps {
  creatorId: string;
  displayName: string | null;
  avatarUrl: string | null | undefined;
  bio: string | null | undefined;
  otherScenariosCount: number;
}
