import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { StudioWorkspacePage } from "../pages/StudioWorkspacePage";

export interface RenderStudioOptions {
  path?: string;
}

export const renderStudio = ({ path = "/studio/new" }: RenderStudioOptions = {}) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const view = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/studio/new" element={<StudioWorkspacePage />} />
          <Route path="/studio/:id/edit" element={<StudioWorkspacePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...view, queryClient };
};
