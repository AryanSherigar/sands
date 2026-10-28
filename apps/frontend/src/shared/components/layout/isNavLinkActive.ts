import type { PrimaryNavLink } from "@/shared/constants/navigation";

export const isNavLinkActive = (
  link: PrimaryNavLink,
  pathname: string,
): boolean =>
  link.isExact ? pathname === link.to : pathname.startsWith(link.to);
