export interface StyleChip {
  id: string;
  label: string;
  wording: string;
}

export const STYLE_CHIP_QUESTION_PREFIX = "style-chip-";

export const STYLE_CHIPS: readonly StyleChip[] = [
  {
    id: "like-a-novel",
    label: "Like a novel",
    wording:
      "Write in rich, flowing prose with full paragraphs, vivid description and a steady literary voice.",
  },
  {
    id: "short-and-punchy",
    label: "Short & punchy",
    wording:
      "Keep it tight. Use short sentences and little description, and move the story forward fast.",
  },
  {
    id: "dark-and-gritty",
    label: "Dark & gritty",
    wording:
      "Be raw and unsparing. Describe hardship and consequences plainly, with a bleak, realistic edge.",
  },
  {
    id: "cozy",
    label: "Cozy",
    wording:
      "Keep a warm, gentle tone. Dwell on small comforts and kindness, and keep danger soft and brief.",
  },
  {
    id: "funny",
    label: "Funny",
    wording:
      "Be playful and witty. Lean on dry humour and absurd details without breaking the story's logic.",
  },
  {
    id: "like-a-game-master",
    label: "Like a game master",
    wording:
      "Narrate like a tabletop game master: set the scene, speak for the characters, and end each reply by asking what the player does next.",
  },
  {
    id: "poetic",
    label: "Poetic",
    wording:
      "Write lyrically, with imagery, rhythm and metaphor, and let the language carry the mood.",
  },
];
