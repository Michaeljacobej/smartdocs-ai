"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DocumentPreview } from "@/components/DocumentPreview";
import { ExtractedDataForm } from "@/components/ExtractedDataForm";
import { OCRViewer } from "@/components/OCRViewer";
import { ProcessingStatus } from "@/components/ProcessingStatus";
import { SummaryCard } from "@/components/SummaryCard";
import { getDocument } from "@/lib/api";
import { DocumentItem } from "@/types/document";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      const data = await getDocument(params.id);
      setDocument(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load document");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const timer = setInterval(() => {
      void load();
    }, 4000);
    return () => clearInterval(timer);
  }, [params.id]);

  if (loading) {
    return <main className="max-w-6xl mx-auto p-6">Loading...</main>;
  }

  if (error || !document) {
    return (
      <main className="max-w-6xl mx-auto p-6">
        <p className="text-rose-600">{error || "Document not found"}</p>
        <Link href="/" className="text-slate-700 underline">Back to dashboard</Link>
      </main>
    );
  }

  return (
    <main className="max-w-6xl mx-auto p-5 md:p-8 space-y-6">
      <section className="panel p-5 md:p-6">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-bold">Document Detail</h1>
          <Link href="/" className="px-3 py-2 rounded-lg bg-slate-900 text-white text-sm">Back</Link>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3 mt-5 text-sm">
          <div>
            <p className="text-slate-500">File Name</p>
            <p className="font-medium">{document.file_name}</p>
          </div>
          <div>
            <p className="text-slate-500">Document Type</p>
            <p className="font-medium">{document.document_type || "-"}</p>
          </div>
          <div>
            <p className="text-slate-500">Upload Date</p>
            <p className="font-medium">{new Date(document.upload_date).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-slate-500">Processing Status</p>
            <ProcessingStatus status={document.processing_status} />
          </div>
        </div>

        {document.processing_status === "FAILED" ? (
          <p className="mt-3 text-rose-600 text-sm">Processing failed: {document.ocr_result?.error_message || "Unknown error"}</p>
        ) : null}
      </section>

      <DocumentPreview document={document} />
      <OCRViewer text={document.ocr_result?.raw_text || null} />
      <ExtractedDataForm document={document} onSaved={() => void load()} />
      <SummaryCard document={document} onUpdated={() => void load()} />
    </main>
  );
}
