"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { DashboardAnalytics } from "@/components/DashboardAnalytics";
import { DocumentTable } from "@/components/DocumentTable";
import { UploadDropzone } from "@/components/UploadDropzone";
import { listDocuments } from "@/lib/api";
import { DocumentItem } from "@/types/document";

export default function HomePage() {
  const router = useRouter();
  const [items, setItems] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      const docs = await listDocuments();
      setItems(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const t = setInterval(() => {
      void load();
    }, 4000);
    return () => clearInterval(t);
  }, []);

  return (
    <main className="max-w-6xl mx-auto p-5 md:p-8 space-y-6">
      <section className="panel p-6 md:p-8 animate-rise">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Dashboard</p>
        <h1 className="text-3xl md:text-4xl font-bold mt-2">AI Document Processing Portal</h1>
        <p className="text-slate-600 mt-3 max-w-3xl">
          Upload transaction documents, run OCR and AI extraction, validate outputs, then review corrections with full traceability.
        </p>
      </section>

      <UploadDropzone onUploaded={(id) => router.push(`/documents/${id}`)} />

      {loading ? <div className="panel p-5">Loading analytics...</div> : <DashboardAnalytics items={items} />}

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Documents</h2>
          <button onClick={() => void load()} className="px-3 py-2 rounded-lg bg-slate-900 text-white text-sm">
            Refresh
          </button>
        </div>
        {loading ? <div className="panel p-5">Loading...</div> : <DocumentTable items={items} onDeleted={() => void load()} />}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      </section>
    </main>
  );
}
