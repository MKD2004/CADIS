import { createContext, useContext, useState, useCallback } from "react";

const DocumentContext = createContext(null);

export function DocumentProvider({ children }) {
  const [doc, setDoc] = useState(null);

  const clearDoc = useCallback(() => setDoc(null), []);

  return (
    <DocumentContext.Provider value={{ doc, setDoc, clearDoc }}>
      {children}
    </DocumentContext.Provider>
  );
}

export function useDocument() {
  const ctx = useContext(DocumentContext);
  if (!ctx) throw new Error("useDocument must be used within DocumentProvider");
  return ctx;
}
