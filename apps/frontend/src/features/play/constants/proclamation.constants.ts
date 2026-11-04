export interface ProclamationSpeakerStyle {
  label: string;
  initial: string;
  ruleClassName: string;
  avatarClassName: string;
  nameClassName: string;
}

export const PROCLAMATION_SPEAKER_STYLES: Record<string, ProclamationSpeakerStyle> = {
  CHANCELLOR: {
    label: "Lord Chancellor Morvath",
    initial: "M",
    ruleClassName: "border-primary-container-wilds",
    avatarClassName: "bg-primary-container-wilds/10 text-primary-container-wilds",
    nameClassName: "text-primary-container-wilds",
  },
  MARSHAL: {
    label: "High Marshal Vane",
    initial: "V",
    ruleClassName: "border-meadow-green",
    avatarClassName: "bg-meadow-green/15 text-meadow-green",
    nameClassName: "text-meadow-green",
  },
  TREASURER: {
    label: "Lord Treasurer Hest",
    initial: "H",
    ruleClassName: "border-tertiary",
    avatarClassName: "bg-tertiary/15 text-tertiary",
    nameClassName: "text-tertiary",
  },
  PRELATE: {
    label: "Arch-Prelate Tomas",
    initial: "T",
    ruleClassName: "border-secondary",
    avatarClassName: "bg-secondary/15 text-secondary",
    nameClassName: "text-secondary",
  },
  COUNCIL: {
    label: "The Council",
    initial: "C",
    ruleClassName: "border-outline",
    avatarClassName: "bg-surface-container-high text-on-surface-variant",
    nameClassName: "text-on-surface-variant",
  },
};

export interface ProclamationStanceStyle {
  label: string;
  icon: string;
  className: string;
}

export const PROCLAMATION_STANCE_STYLES: Record<string, ProclamationStanceStyle> = {
  support: {
    label: "Support",
    icon: "check_circle",
    className: "bg-meadow-green/20 text-[#294c26]",
  },
  cautious: {
    label: "Cautious",
    icon: "help_outline",
    className: "bg-secondary-fixed text-on-secondary-container",
  },
  oppose: {
    label: "Oppose",
    icon: "cancel",
    className: "bg-tertiary-fixed text-on-tertiary-fixed-variant font-bold",
  },
};

export const PROCLAMATION_ESTATE_STYLES: Record<string, string> = {
  nobility: "bg-primary-container-wilds/15 text-primary-container-wilds",
  military: "bg-meadow-green/15 text-meadow-green",
  burghers: "bg-tertiary/15 text-tertiary",
  clergy: "bg-secondary/15 text-secondary",
};

export const PROCLAMATION_EMPTY_TITLE = "The Chamber Sits in Solemn Silence";
export const PROCLAMATION_EMPTY_BODY =
  "The scribes lay out their quills upon virgin parchment. The council falls silent awaiting the decree of the Sovereign.";
export const PROCLAMATION_ENACTING_LABEL = "Affixing Great Seal to Parchment...";
