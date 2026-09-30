"use client";

import { useState } from "react";

import { generateSummary } from "@/lib/api";
import { DocumentItem } from "@/types/document";

export function SummaryCard({ document, onUpdated }: { document: DocumentItem; onUpdated: () => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    try {
      setLoading(true);
      setError(null);
      await generateSummary(document.id);
      onUpdated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate summary");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel p-4 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-lg font-semibold">AI Summary</h3>
        <button
          onClick={handleGenerate}
          disabled={loading || document.processing_status === "PROCESSING"}
          className="px-4 py-2 rounded-lg bg-ink text-white disabled:opacity-60"
        >
          {loading ? "Generating..." : "Generate Summary"}
        </button>
      </div>
      <p className="text-sm text-slate-600">
        {document.summary?.summary_text || "Summary not generated yet."}
      </p>
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
    </div>
  );
}
