import type {
  TerrainType,
  WeatherType,
} from "../components/StrategyWarCouncil/StrategyWarCouncil.types";

const TERRAIN_LABELS: Record<TerrainType, string> = {
  plains: "Open Plains",
  forest: "Forest",
  hills: "Hills",
  mountain: "Mountain Pass",
  marsh: "Marsh",
  desert: "Desert",
  river: "River Ford",
};

const WEATHER_LABELS: Record<WeatherType, string> = {
  clear: "Clear Skies",
  rain: "Rain",
  severe: "Severe Weather",
};

export const formatTerrainLabel = (terrain: TerrainType): string => TERRAIN_LABELS[terrain];

export const formatWeatherLabel = (weather: WeatherType): string => WEATHER_LABELS[weather];
