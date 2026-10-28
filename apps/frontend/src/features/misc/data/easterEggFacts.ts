import type { EasterEggFact, FactCategory } from "../types/easterEgg.types";

export const EASTER_EGG_FACTS: EasterEggFact[] = [
  {
    id: "anime-rezero",
    category: "anime",
    title: "Re:Zero",
    fact: "Re:Zero is the best anime",
    tags: ["isekai", "psychological", "fantasy"],
  },
  {
    id: "anime-grimgar",
    category: "anime",
    title: "Grimgar of Fantasy and Ash",
    fact: "Grimgar is very good",
    tags: ["fantasy", "survival", "drama"],
  },
  {
    id: "song-i-cannot-say",
    category: "song",
    title: "I cannot say - Junko Kamata",
    fact: "Try the song 'I cannot say' By Junko Kamata",
    tags: ["acoustic", "ballad", "japanese"],
  },
  {
    id: "song-song-of-the-ancients",
    category: "song",
    title: "Song of the Ancients (Devola)",
    fact: "Song of the Ancients(Devola) is nerve-breaking",
    tags: ["nier", "soundtrack", "mystic"],
  },
  {
    id: "anime-grieving-souls",
    category: "anime",
    title: "Grieving Souls",
    fact: "Are you bored? Try Grieving Souls",
    tags: ["adventure", "comedy", "fantasy"],
  },
];

const getFactsByCategory = (
  category?: FactCategory,
): EasterEggFact[] => {
  if (!category) {
    return EASTER_EGG_FACTS;
  }
  return EASTER_EGG_FACTS.filter((fact) => fact.category === category);
};

export const getRandomFact = (category?: FactCategory): EasterEggFact => {
  const pool = getFactsByCategory(category);
  const randomIndex = Math.floor(Math.random() * pool.length);
  return pool[randomIndex];
};

export const searchFacts = (query: string): EasterEggFact[] => {
  const normalizedQuery = query.toLowerCase().trim();
  return EASTER_EGG_FACTS.filter((fact) => {
    const is_title_match = fact.title.toLowerCase().includes(normalizedQuery);
    const is_fact_match = fact.fact.toLowerCase().includes(normalizedQuery);
    const is_tag_match = fact.tags.some((tag) =>
      tag.toLowerCase().includes(normalizedQuery),
    );
    return is_title_match || is_fact_match || is_tag_match;
  });
};
