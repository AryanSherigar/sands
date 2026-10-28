import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { logEvent } from "@/shared/lib/logger";
import { emitClientError } from "@/shared/lib/alpha-client-error";
import { initializeAuthInterceptors } from "@/features/auth/lib/setupAuthInterceptor";
import "../index.css";

initializeAuthInterceptors();

window.addEventListener("error", (event) => {
  logEvent("error", "unhandled_frontend_error", {
    message: event.message,
    stack: event.error?.stack,
  });
  emitClientError("window_error", event.error);
});

window.addEventListener("unhandledrejection", (event) => {
  logEvent("error", "unhandled_frontend_error", {
    message: String(event.reason),
    stack: event.reason?.stack,
  });
  emitClientError("unhandled_rejection", event.reason);
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
