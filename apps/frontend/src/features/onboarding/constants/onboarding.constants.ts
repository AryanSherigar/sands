export const ONBOARDING_STEP_IDS = [
  "welcome",
  "genres",
  "profile",
  "reading",
  "done",
] as const;

export const INPUT_STEP_IDS = ["genres", "profile", "reading"] as const;

export const MAX_PREFERRED_GENRES = 3;
export const MAX_DISPLAY_NAME_LENGTH = 255;
export const MAX_BIO_LENGTH = 160;

export const ONBOARDING_ERROR_MESSAGE =
  "We couldn't save your setup. Please try again.";

export const INPUT_STEP_LABELS: Record<(typeof INPUT_STEP_IDS)[number], string> = {
  genres: "Genres",
  profile: "Profile",
  reading: "Reading",
};

export const RECOMMENDATION_SKELETON_COUNT = 3;

export interface GenreMeta {
  color: string;
  subtitle: string;
  storyPreview: string;
}

export const GENRE_METADATA: Record<string, GenreMeta> = {
  "Noir / Detective": {
    color: "#C79A74",
    subtitle: "Rain-slick streets & conspiracies",
    storyPreview: "The Grey Ledger · 6 stories",
  },
  "Sci-Fi": {
    color: "#7FB8C9",
    subtitle: "Deep cold space & anomalies",
    storyPreview: "Substratum 9 · 8 stories",
  },
  "High Fantasy": {
    color: "#CDBB8E",
    subtitle: "Monoliths, covenants & archives",
    storyPreview: "Archivist of Oakhaven · 5 stories",
  },
  Cyberpunk: {
    color: "#C58BC9",
    subtitle: "Chrome, telemetry & neural firewalls",
    storyPreview: "Neon Meridian · 4 stories",
  },
  Horror: {
    color: "#D0777C",
    subtitle: "Dread, liminal isolation & sanity checks",
    storyPreview: "Whispers of Sker · 3 stories",
  },
  "Adventure/Survival": {
    color: "#8FB27A",
    subtitle: "Uncharted wilderness & resource trials",
    storyPreview: "Rift Frontier · 2 stories",
  },
  Mystery: {
    color: "#8E9BDB",
    subtitle: "Puzzles, unsealed ciphers & clues",
    storyPreview: "The Hollow Cipher · 2 stories",
  },
  "Post-Apocalyptic/Dystopian": {
    color: "#AFAE8C",
    subtitle: "Sunken ruins & scavenging remnants",
    storyPreview: "Dust & Ash · 1 story",
  },
  "Slice of Life": {
    color: "#D29BB2",
    subtitle: "Quiet bonds, daily rituals & dialogue",
    storyPreview: "Teahouse by the Bay · 1 story",
  },
  "Historical Fiction": {
    color: "#BFA38A",
    subtitle: "Authentic epochs & forgotten records",
    storyPreview: "Iron & Treaty · 1 story",
  },
};

export interface AtmosphericBanner {
  id: string;
  name: string;
  url: string;
}

export const ATMOSPHERIC_BANNER_PRESETS: AtmosphericBanner[] = [
  {
    id: "obsidian",
    name: "Obsidian",
    url: "https://lh3.googleusercontent.com/aida/AEtjO1V9mvsDMVknWrE5M4wHezo4r9bA3oRYrC3206UnoETKUX7CguLN6vxXvog8Ej4Fhk_RuFSVL69HZn-r09UQ5Sdu85Eos_vUKb7WYvkPht1QGzt3m61r-xJ2YkF3uHiihJmt8PZmx0LmNQU01P9i6TM1iRLMbo07cLZwx-9wEljoyScf9soGaxMqsS4DNM2T6WweZAVRkj7DDKbtT6rIPwK5m9-jbPKJN3HRoduHfZmlqL-weq8mhYxpqxE",
  },
  {
    id: "deep-ice",
    name: "Deep Ice",
    url: "https://lh3.googleusercontent.com/aida/AEtjO1Wq-nmfYVWqz32ttwYobShfb7T4vGijXtEELWzhUt1QDfqcEhABQRfCYljaF1KkOgNaylGMYRFznPrl1V41ovainuXVzovgeiMnJnMQfa8ezPoVnkDB3AT5kZUiKeYNkH2I-s6AqoExgyFHB2BfRhBjDjDbVOJ-owQC7dGjwwjVYEObHi3AtVRkcr1FGhI43-_TTBVMF2UzCk2FTS5F6WAu6hkQg-cLa0FdysOx_3ReUNenIRW7L109iLC_",
  },
  {
    id: "chiaroscuro",
    name: "Chiaroscuro",
    url: "https://lh3.googleusercontent.com/aida/AEtjO1U0rEVlwrQiDFJg_B2U7NyBN1Tc6E9Zku32EOs6qGCvX9PMy9OMqVexdz0FdrqYMslaWIkPIHXMj3ZitI_OrloQNoQ6GT9O2Robkbi1ATtWz5ZTK1QPWV-4Y3dNzjqf6KamLonPm_W33h6AefTsR6ZoUyBQIpmYpY87kXJ8ufs-rDh34rwXVo6qRx6TnqNFR6W14CchK_i8WW73usbqjxYj_r9fa1HDDPkd5orCxqiLdyaSTvJlc8nXeaA",
  },
  {
    id: "archive",
    name: "Archive",
    url: "https://lh3.googleusercontent.com/aida/AEtjO1XqTXkUt4r2jutUFEIRkiG400KpMJbV1m5v5xGYwCDvV38OoEusTqbZmZCl45dFK84CsQPZX_e2-CrvpVjHPjuO4HekVDWamTUEWKPuRemu0nu3UVeC0k_8WOF7Pi7QeD6CkAFT4wMhB4CH4gaMBhu8vIIp7aSzkQ2UysqrEiDlP0LH_p7TKbXJ4ehiKlTK9Np4cZOvdmzoWBHO_E-Iq00Xi3xA2by5Ftc334uMnTiNBXOTxoEAHLc-Csc",
  },
];

export interface ScenarioRecommendation {
  id: string;
  title: string;
  genre: string;
  description: string;
  imageUrl: string;
  genreColor: string;
  rating: number;
  plays: string;
}

export const SHOWCASE_RECOMMENDATIONS: ScenarioRecommendation[] = [
  {
    id: "grey-ledger",
    title: "The Grey Ledger",
    genre: "Noir / Detective",
    description:
      "1947, New Providence. A missing city comptroller and carbon-copy ledger pages.",
    imageUrl: ATMOSPHERIC_BANNER_PRESETS[2].url,
    genreColor: "#C79A74",
    rating: 4.9,
    plays: "3.4k",
  },
  {
    id: "substratum-9",
    title: "Substratum 9",
    genre: "Sci-Fi",
    description:
      "Deep subterranean research facility buried under frozen tundra where telemetry has ceased.",
    imageUrl: ATMOSPHERIC_BANNER_PRESETS[1].url,
    genreColor: "#7FB8C9",
    rating: 4.8,
    plays: "2.1k",
  },
  {
    id: "archivist-of-oakhaven",
    title: "Archivist of Oakhaven",
    genre: "High Fantasy",
    description:
      "Records of twelve forgotten dynasties and an unsealed cipher in the monolithic spire.",
    imageUrl: ATMOSPHERIC_BANNER_PRESETS[3].url,
    genreColor: "#CDBB8E",
    rating: 4.7,
    plays: "1.8k",
  },
];
