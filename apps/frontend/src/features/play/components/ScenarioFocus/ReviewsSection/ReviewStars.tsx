import React from "react";
import { IconStar, IconStarFilled } from "@tabler/icons-react";

const STAR_VALUES = [1, 2, 3, 4, 5];

interface ReviewStarsProps {
  value: number;
  size?: number;
}

export const ReviewStars: React.FC<ReviewStarsProps> = ({
  value,
  size = 14,
}) => (
  <span aria-hidden="true" className="flex items-center gap-0.5 text-accent">
    {STAR_VALUES.map((star) =>
      star <= value ? (
        <IconStarFilled key={star} size={size} />
      ) : (
        <IconStar key={star} size={size} className="text-content-faint" />
      ),
    )}
  </span>
);
