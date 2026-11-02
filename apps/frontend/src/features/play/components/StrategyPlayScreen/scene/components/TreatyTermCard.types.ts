export type TreatyTermTone = "green" | "amber" | "sky" | "purple" | "rose";

export interface TreatyTermView {
  title: string;
  badge: string;
  icon: string;
  tone: TreatyTermTone;
  detail: string;
}

export interface TreatyTermCardProps {
  view: TreatyTermView;
}
