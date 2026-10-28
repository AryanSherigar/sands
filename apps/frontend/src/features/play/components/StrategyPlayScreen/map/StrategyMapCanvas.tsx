import React from "react";
import { RegionOutlineLayer } from "@/shared/components/RegionOutlineLayer/RegionOutlineLayer";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import { buildOwnershipFillClasses } from "../../../lib/ownershipStyles";
import type { ArmyView, CampaignWorldView } from "../../../types/simulation.types";
import type { SelectedEntity } from "../../../stores/strategyPlay.types";
import type { StrategyMapCanvasProps } from "./StrategyMap.types";
import { SettlementPin } from "./pins/SettlementPin";
import { ArmyBannerPin } from "./pins/ArmyBannerPin";
import { CrisisAlertPin } from "./pins/CrisisAlertPin";
import { StrategySituationPins } from "./StrategySituationPins";

const ARMY_PIN_STACK_OFFSET_PX = 34;
const UNREST_CRISIS_THRESHOLD = 50;

function computeTroopCount(army: ArmyView): number {
  if (army.troops && Object.keys(army.troops).length > 0) {
    return Object.values(army.troops).reduce(
      (sum: number, count: number) => sum + count,
      0,
    );
  }
  if (army.size_estimate) {
    return army.size_estimate.high;
  }
  return 0;
}

function renderArmyPin(
  army: ArmyView,
  region: MapRegion,
  myFactionId: string,
  selectedEntity: SelectedEntity | null | undefined,
  onSelectEntity: (entity: SelectedEntity | null) => void,
  stackIndex: number,
): React.ReactElement {
  const isHostile = army.owner_id !== myFactionId;
  const isSelected = selectedEntity?.type === "army" && selectedEntity.id === army.army_id;
  const troopCount = computeTroopCount(army);

  return (
    <ArmyBannerPin
      key={army.army_id}
      armyId={army.army_id}
      commanderName={army.commander_name}
      troopCount={troopCount}
      coords={{
        x: region.label_point.x,
        y: region.label_point.y - stackIndex * ARMY_PIN_STACK_OFFSET_PX,
      }}
      isHostile={isHostile}
      isSelected={isSelected}
      onClick={(id) => onSelectEntity({ type: "army", id })}
    />
  );
}

function renderMapArmies(
  regions: MapRegion[],
  armies: ArmyView[] | undefined,
  myFactionId: string | undefined,
  selectedEntity: SelectedEntity | null | undefined,
  onSelectEntity: (entity: SelectedEntity | null) => void,
): React.ReactElement[] {
  if (!armies || !myFactionId) return [];
  const regionMap = new Map(regions.map((r) => [r.id, r]));
  const pins: React.ReactElement[] = [];
  const armiesPerRegion = new Map<string, number>();

  for (const army of armies) {
    const region = regionMap.get(army.location_id);
    if (!region) continue;
    const stackIndex = armiesPerRegion.get(region.id) ?? 0;
    armiesPerRegion.set(region.id, stackIndex + 1);
    pins.push(
      renderArmyPin(army, region, myFactionId, selectedEntity, onSelectEntity, stackIndex),
    );
  }
  return pins;
}

function renderSettlementPins(
  regions: MapRegion[],
  selectedEntity: SelectedEntity | null | undefined,
  onSelectEntity: (entity: SelectedEntity | null) => void,
): React.ReactElement[] {
  return regions.map((region) => {
    const isSelected = selectedEntity?.type === "region" && selectedEntity.id === region.id;
    return (
      <SettlementPin
        key={region.id}
        name={region.name}
        regionId={region.id}
        coords={region.label_point}
        isSelected={isSelected}
        onClick={(id) => onSelectEntity({ type: "region", id })}
      />
    );
  });
}

function renderCrisisAlerts(
  regions: MapRegion[],
  worldRegions: CampaignWorldView["regions"] | undefined,
): React.ReactElement[] {
  if (!worldRegions) return [];
  const regionMap = new Map(regions.map((r) => [r.id, r]));
  const alerts: React.ReactElement[] = [];

  for (const item of worldRegions) {
    const unrest = item.detail?.unrest ?? 0;
    if (unrest < UNREST_CRISIS_THRESHOLD) continue;
    const region = regionMap.get(item.region_id);
    if (!region) continue;
    alerts.push(
      <CrisisAlertPin
        key={`crisis-${region.id}`}
        coords={region.label_point}
        label={`Unrest ${unrest}%`}
      />,
    );
  }
  return alerts;
}

export const StrategyMapCanvas: React.FC<StrategyMapCanvasProps> = ({
  document,
  world,
  selectedEntity,
  onSelectEntity,
  situations,
  onSelectSituation,
}) => {
  const selectedRegionIds = selectedEntity?.type === "region" ? [selectedEntity.id] : [];
  const handleBackgroundClick = () => onSelectEntity(null);
  const handleRegionClick = (id: string) => onSelectEntity({ type: "region", id });
  const regionFillClasses =
    world && world.regions.length > 0
      ? buildOwnershipFillClasses(world.regions, world.my_faction.id)
      : undefined;

  const centroids = React.useMemo(
    () =>
      Object.fromEntries(
        document.regions.map((r) => [
          r.id,
          r.label_point ?? { x: 0, y: 0 },
        ]),
      ),
    [document.regions],
  );

  return (
    <div
      className="relative select-none bg-[#F3EAD3]"
      style={{ width: document.width, height: document.height }}
      onClick={handleBackgroundClick}
    >
      {document.image_url ? (
        <img
          src={document.image_url}
          alt="Grand Strategy Map"
          className="absolute inset-0 w-full h-full object-cover filter contrast-[1.02] brightness-[0.99]"
        />
      ) : null}

      <div className="absolute inset-0 pointer-events-none bg-gradient-to-tr from-[#DCE7EA]/20 via-transparent to-[#C7D3D6]/30 mix-blend-multiply" />

      <svg
        className="absolute inset-0 w-full h-full pointer-events-none [&_path]:pointer-events-auto"
        viewBox={`0 0 ${document.width} ${document.height}`}
      >
        <RegionOutlineLayer
          document={document}
          targetSize={{ width: document.width, height: document.height }}
          selectedIds={selectedRegionIds}
          regionFillClasses={regionFillClasses}
          onRegionClick={handleRegionClick}
        />
        {situations && situations.length > 0 && (
          <StrategySituationPins
            situations={situations}
            centroids={centroids}
            onSelectSituation={
              onSelectSituation ??
              ((_, regionId) => onSelectEntity({ type: "region", id: regionId }))
            }
          />
        )}
      </svg>

      {renderSettlementPins(document.regions, selectedEntity, onSelectEntity)}
      {renderMapArmies(
        document.regions,
        world?.armies,
        world?.my_faction?.id,
        selectedEntity,
        onSelectEntity,
      )}
      {renderCrisisAlerts(document.regions, world?.regions)}
    </div>
  );
};
