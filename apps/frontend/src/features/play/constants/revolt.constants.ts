export const NO_TERMS_OPTION_ID = "no_terms";

export const REVOLT_OPTION_OUTCOMES: Readonly<Record<string, string>> = {
  no_terms: "You offered fair words and nothing more.",
  tax_relief: "Taxes in the region are lowered, and you have sworn to keep them low.",
  garrison_out: "You have sworn to keep your armies out of the region.",
  relief_small: "The granaries were opened and a small relief paid.",
  relief_large: "A great relief was paid from the treasury.",
  amnesty: "The rebels are pardoned, and you have sworn not to crack down on them.",
  charter: "A charter was granted: lower taxes and no soldiers in the region.",
};

export const REVOLT_FALLBACK_OUTCOME = "The people have been answered.";
