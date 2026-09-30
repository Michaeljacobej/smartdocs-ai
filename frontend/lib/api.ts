import { CorrectionPayload, DocumentItem, DocumentListResponse, Summary } from "@/types/document";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function safeFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
  });

  if (!response.ok) {
    let message = "Unexpected request error";
    try {
      const payload = await response.json();
      message = payload?.error?.message || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const data = await safeFetch<DocumentListResponse>("/documents");
  return data.items;
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append("file", file);
  return safeFetch<DocumentItem>("/documents", {
    method: "POST",
    body: formData,
  });
}

export async function getDocument(documentId: string): Promise<DocumentItem> {
  return safeFetch<DocumentItem>(`/documents/${documentId}`);
}

export async function deleteDocument(documentId: string): Promise<void> {
  await safeFetch<void>(`/documents/${documentId}`, { method: "DELETE" });
}

export async function updateExtractedData(documentId: string, payload: CorrectionPayload): Promise<DocumentItem> {
  return safeFetch<DocumentItem>(`/documents/${documentId}/extracted-data`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function generateSummary(documentId: string): Promise<Summary> {
  const data = await safeFetch<{ summary: Summary }>(`/documents/${documentId}/summary`, {
    method: "POST",
  });
  return data.summary;
}

export function documentFileUrl(documentId: string): string {
  return `${API_BASE_URL}/documents/${documentId}/file`;
}
