import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { DocumentProvider } from "./context/DocumentContext.jsx";
import "./index.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <DocumentProvider>
        <App />
      </DocumentProvider>
    </BrowserRouter>
  </StrictMode>
);
