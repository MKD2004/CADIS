import axios from "axios";

const BASE = import.meta.env.VITE_API_URL || "";

const api = axios.create({
  baseURL: BASE,
  timeout: 120_000,
});

export async function checkHealth() {
  const { data } = await api.get("/health");
  return data;
}

export async function fetchSamples() {
  const { data } = await api.get("/api/samples");
  return data || [];
}

export async function processPdf(file, onProgress) {
  const form = new FormData();
  form.append("file", file);

  const { data } = await api.post("/api/process-pdf", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: onProgress,
  });
  return data;
}

export async function analyzeSample(docId) {
  const { data } = await api.post(`/api/sample-analyze/${docId}`);
  return data;
}

export async function chat(query, documentId = "current") {
  const { data } = await api.post("/api/chat", { query, document_id: documentId });
  return data;
}
