import type { TacticType, TerrainType } from "../StrategyWarCouncil.types";
import { DoctrineCard } from "./DoctrineCard";

export interface TacticalDoctrinesListProps {
  selectedTactic: TacticType;
  onSelectTactic: (tactic: TacticType) => void;
  cavalryCount?: number;
  terrain?: TerrainType;
}

interface DoctrineConfig {
  tactic: TacticType;
  title: string;
  latinName: string;
  description: string;
  riskNote: string;
  prerequisite: string;
  isLocked: boolean;
  lockReason?: string;
}

function formatTerrainLabel(terrain?: TerrainType): string {
  if (terrain === "river") return "River Ford";
  if (terrain === "plains") return "Plains";
  if (terrain === "hills") return "Hills";
  if (terrain === "mountain") return "Mountain";
  if (terrain === "marsh") return "Marsh";
  if (terrain === "desert") return "Desert";
  if (terrain === "forest") return "Forest";
  return "Open Ground";
}

function checkIsSelected(tactic: TacticType, selectedTactic: TacticType): boolean {
  if (tactic === "hold") {
    return selectedTactic === "hold" || selectedTactic === "hold_high_ground";
  }
  return selectedTactic === tactic;
}

function buildForestAmbuscade(terrain?: TerrainType): DoctrineConfig {
  const isForest = terrain === "forest";
  const terrainLabel = formatTerrainLabel(terrain);
  return {
    tactic: "forest_flank",
    title: "Forest Ambuscade",
    latinName: "Insidiae Silvestres",
    description: "+40% surprise shock assault launched from dense canopy cover.",
    riskNote: "Risk: Requires forest cover; ruined if spotted by enemy outriders.",
    prerequisite: "Prerequisite: Dense canopy cover for concealed deployment.",
    isLocked: !isForest,
    lockReason: `Locked: Requires Forest terrain (Current: ${terrainLabel}).`,
  };
}

const BASE_DOCTRINES: Omit<DoctrineConfig, "isLocked">[] = [
  {
    tactic: "press",
    title: "Boar's Snout Wedge Shock",
    latinName: "Caput Porcinum",
    description: "Shock thrust: heavy knights in rear rank launch armored counter-thrust.",
    riskNote: "Risk: High risk if front line crumbles before shock thrust.",
    prerequisite: "Prerequisite: Armored vanguard & shock cavalry reserve (min 15% cavalry ratio).",
  },
  {
    tactic: "hold",
    title: "Shield-Wall Anchor",
    latinName: "Fulcum",
    description: "Maximizes defense, locks shields against enemy assault.",
    riskNote: "Risk: Immobile; vulnerable to heavy missile fire and rear envelopment.",
    prerequisite: "Prerequisite: Shield-bearing infantry braced in front rank.",
  },
  {
    tactic: "feigned_retreat",
    title: "Feigned Retreat",
    latinName: "Simulata Fuga",
    description: "Front line yields ground into bottleneck; rear knights wheel to envelop.",
    riskNote: "Risk: Catastrophic collapse if front rank routs for real.",
    prerequisite: "Prerequisite: Disciplined veteran line & fast cavalry wings.",
  },
];

function getHistoricalDoctrines(terrain?: TerrainType): DoctrineConfig[] {
  const base = BASE_DOCTRINES.map((doctrine) => ({ ...doctrine, isLocked: false }));
  return [...base, buildForestAmbuscade(terrain)];
}

export function TacticalDoctrinesList({
  selectedTactic,
  onSelectTactic,
  terrain,
}: TacticalDoctrinesListProps) {
  const doctrines = getHistoricalDoctrines(terrain);

  return (
    <div className="flex flex-col gap-2">
      {doctrines.map((doctrine) => (
        <DoctrineCard
          key={doctrine.tactic}
          tactic={doctrine.tactic}
          title={doctrine.title}
          latinName={doctrine.latinName}
          description={doctrine.description}
          riskNote={doctrine.riskNote}
          prerequisite={doctrine.prerequisite}
          isSelected={checkIsSelected(doctrine.tactic, selectedTactic)}
          isLocked={doctrine.isLocked}
          lockReason={doctrine.lockReason}
          onSelect={() => onSelectTactic(doctrine.tactic)}
        />
      ))}
    </div>
  );
}
