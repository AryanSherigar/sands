import { FALLBACK_COVER_IMAGE_URLS } from "../constants/landing.constants";

const hashScenarioId = (scenarioId: string): number =>
  [...scenarioId].reduce(
    (total, character) => total + (character.codePointAt(0) ?? 0),
    0,
  );

export const resolveCoverImage = (
  coverImageUrl: string | null,
  scenarioId: string,
): string =>
  coverImageUrl ??
  FALLBACK_COVER_IMAGE_URLS[
    hashScenarioId(scenarioId) % FALLBACK_COVER_IMAGE_URLS.length
  ];
