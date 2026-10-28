import React from "react";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import { ScenarioMiniCard } from "../cards/ScenarioMiniCard";
import type { CreationsGridProps } from "./CreationsGrid.types";

export const CreationsGrid: React.FC<CreationsGridProps> = ({ items }) => (
  <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
    {items.map((scenario) => {
      const isPublished = scenario.status === "published";
      return (
        <ScenarioMiniCard
          key={scenario.scenario_id}
          scenario={scenario}
          footerAction={
            <ButtonLink
              to={
                isPublished
                  ? `/scenario/${scenario.scenario_id}`
                  : `/studio/${scenario.scenario_id}/edit`
              }
              variant="ghost"
              size="sm"
            >
              {isPublished ? "View" : "Edit draft"}
            </ButtonLink>
          }
        />
      );
    })}
  </div>
);
