import { IconFeather, IconMail } from "@tabler/icons-react";
import type { Icon } from "@tabler/icons-react";

const TEMPERAMENT_ICONS: Record<string, Icon> = {
  mail: IconMail,
  peaceful: IconFeather,
};

export function TemperamentIcon({ name }: { name: string }) {
  const Glyph = TEMPERAMENT_ICONS[name] ?? IconMail;
  return <Glyph size={14} aria-hidden="true" />;
}
