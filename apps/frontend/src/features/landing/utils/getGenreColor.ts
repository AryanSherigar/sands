export const getGenreColor = (genre?: string): string => {
  switch (genre?.toLowerCase()) {
    case "sci-fi":
      return "#7FB8C9";
    case "noir / detective":
    case "noir":
      return "#C79A74";
    case "dark fantasy":
    case "mystery":
      return "#8E9BDB";
    case "high fantasy":
      return "#CDBB8E";
    case "cyberpunk":
      return "#C58BC9";
    case "horror":
      return "#D0777C";
    default:
      return "rgb(var(--accent))";
  }
};
