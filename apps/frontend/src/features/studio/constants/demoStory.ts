import type { GuideStepId } from "./guideSteps";

export interface DemoStepExample {
  heading: string;
  lines: string[];
}

export const DEMO_STORY: Partial<Record<GuideStepId, DemoStepExample>> = {
  idea: {
    heading: "From “The Door Below”",
    lines: [
      "One line idea: A lighthouse keeper finds a door in the sea.",
      "Name: The Door Below",
    ],
  },
  premise: {
    heading: "From “The Door Below”",
    lines: [
      "Mara has kept the Gannet Rock light for thirty years. One low tide, a door appears in the seabed, and it is open.",
      "What stands in her way? The tide gives her an hour, and the village has sworn the sea is empty.",
      "Kind of story: Mystery. Feel: eerie, lonely.",
    ],
  },
  player: {
    heading: "From “The Door Below”",
    lines: [
      "A character I write: Mara, the keeper. Looks: weathered hands, a salt-stiff coat. Carries: a brass lantern and a ring of keys.",
      "Setup choices: Name, Pronouns, Difficulty (Gentle, Normal, Harsh).",
    ],
  },
  characters: {
    heading: "From “The Door Below”",
    lines: [
      "Tomas, the ferryman. Voice: slow, dry, always understating. Wants: to be left alone. Secret: he has seen the door before.",
      "Link: Tomas · is usually found at · The Ferry Jetty.",
    ],
  },
  world: {
    heading: "From “The Door Below”",
    lines: [
      "A cold northern coast where the tide table rules every day. People trust bells and tide charts more than their neighbours.",
      "Always remember: The door only shows at low tide. Nobody has ever come back with a light.",
      "Places: The Lighthouse, The Ferry Jetty. Things: The Brass Lantern.",
    ],
  },
  endings: {
    heading: "From “The Door Below”",
    lines: [
      "Lose ending: The Tide Takes Her. Ends when: Tide time drops to 0.",
      "What the player reads: The water closes over the door. The Gannet Rock light goes out, and nobody on the shore looks up.",
      "Win ending: A Light in the Deep. Ends when: Has the brass lantern becomes yes and Tide time is at least 1.",
    ],
  },
  tracked_values: {
    heading: "From “The Door Below”",
    lines: [
      "Tide time: 0 to 60, starts at 60. Shown as a Bar. What it means: minutes before the sea takes the door back.",
      "Has the brass lantern: Yes / no, starts as no. What it means: Mara has taken the lantern from the jetty.",
    ],
  },
  rules: {
    heading: "From “The Door Below”",
    lines: [
      "When Tide time is at most 10 → Tell the narrator: the water is at her knees and the door groans. Every turn while this is true.",
      "Only once, when Has the brass lantern becomes yes → Tell the narrator: the lamp room brightens and the door answers.",
    ],
  },
  hard_limits: {
    heading: "From “The Door Below”",
    lines: [
      "While Door open is yes → Tide time must be at least 1. In words: the sea never takes the door while it stands open.",
    ],
  },
};
