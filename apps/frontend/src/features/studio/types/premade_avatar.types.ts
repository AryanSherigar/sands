export interface PremadeAvatar {
  id: string;
  name: string;
  style: string;
  avatar_url: string;
  preview_url: string;
  credit: string | null;
}

export interface PremadeAvatarListResponse {
  avatars: PremadeAvatar[];
}
