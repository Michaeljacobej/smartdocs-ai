"use client";

import Link from "next/link";
import { useState } from "react";

import { deleteDocument } from "@/lib/api";
import { DocumentItem } from "@/types/document";

import { ProcessingStatus } from "./ProcessingStatus";

function formatCurrency(value: number | null, currency: string | null): string {
  if (value === null) return "-";
  const code = currency || "USD";
  try {
    return new Intl.NumberFormat("id-ID", { style: "currency", currency: code, maximumFractionDigits: 2 }).format(value);
  } catch {
    return `${value}`;
  }
}

function getReviewState(item: DocumentItem): "REQUIRED" | "NOT_REQUIRED" | "REVIEWED" | "PENDING" | "UNKNOWN" {
  if (item.processing_status === "REVIEW_REQUIRED") return "REQUIRED";
  if (item.processing_status === "REVIEWED") return "REVIEWED";
  if (item.processing_status === "UPLOADED" || item.processing_status === "PROCESSING") return "PENDING";
  if (item.processing_status === "FAILED") return "UNKNOWN";

  const decision = item.extracted_data?.confidence_data?.evaluation?.decision;
  if (decision === "REVIEW") return "REQUIRED";
  if (decision === "ACCEPT") return "NOT_REQUIRED";

  if (item.processing_status === "COMPLETED") return "NOT_REQUIRED";
  return "UNKNOWN";
}

function ReviewBadge({ state }: { state: ReturnType<typeof getReviewState> }) {
  if (state === "REQUIRED") {
    return <span className="inline-flex px-2 py-1 rounded-full text-xs font-semibold bg-orange-100 text-orange-800">Review Required</span>;
  }
  if (state === "NOT_REQUIRED") {
    return <span className="inline-flex px-2 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">No Review Needed</span>;
  }
  if (state === "REVIEWED") {
    return <span className="inline-flex px-2 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800">Reviewed</span>;
  }
  if (state === "PENDING") {
    return <span className="inline-flex px-2 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">Pending</span>;
  }
  return <span className="inline-flex px-2 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-500">-</span>;
}

export function DocumentTable({ items, onDeleted }: { items: DocumentItem[]; onDeleted: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const reviewRequiredCount = items.filter((item) => getReviewState(item) === "REQUIRED").length;
  const notRequiredCount = items.filter((item) => {
    const state = getReviewState(item);
    return state === "NOT_REQUIRED" || state === "REVIEWED";
  }).length;

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this document?")) return;
    try {
      setBusyId(id);
      setError(null);
      await deleteDocument(id);
      onDeleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusyId(null);
    }
  };

  if (!items.length) {
    return <div className="panel p-6 text-slate-600">No documents yet. Upload one to start.</div>;
  }

  return (
    <div className="panel overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-end gap-2 text-xs sm:text-sm">
        <span className="inline-flex px-2 py-1 rounded-full bg-orange-100 text-orange-800 font-medium">
          Review Required: {reviewRequiredCount}
        </span>
        <span className="inline-flex px-2 py-1 rounded-full bg-emerald-100 text-emerald-800 font-medium">
          No Review Needed: {notRequiredCount}
        </span>
      </div>
      <div className="overflow-auto">
        <table className="w-full text-sm min-w-[900px]">
          <thead className="bg-slate-100 text-slate-700">
            <tr>
              <th className="text-left p-3">File Name</th>
              <th className="text-left p-3">Type</th>
              <th className="text-left p-3">Upload Date</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Review</th>
              <th className="text-left p-3">Total</th>
              <th className="text-left p-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const total = item.extracted_data?.total_amount_corrected ?? item.extracted_data?.total_amount_original ?? null;
              const currency = item.extracted_data?.currency_corrected ?? item.extracted_data?.currency_original ?? null;
              const reviewState = getReviewState(item);
              return (
                <tr key={item.id} className="border-t border-slate-200 align-top">
                  <td className="p-3">{item.file_name}</td>
                  <td className="p-3">{item.document_type || "-"}</td>
                  <td className="p-3">{new Date(item.upload_date).toLocaleString()}</td>
                  <td className="p-3"><ProcessingStatus status={item.processing_status} /></td>
                  <td className="p-3"><ReviewBadge state={reviewState} /></td>
                  <td className="p-3">{formatCurrency(total, currency)}</td>
                  <td className="p-3">
                    <div className="flex gap-2">
                      <Link href={`/documents/${item.id}`} className="px-3 py-1 rounded-md bg-slate-900 text-white">
                        View
                      </Link>
                      <button
                        onClick={() => void handleDelete(item.id)}
                        disabled={busyId === item.id}
                        className="px-3 py-1 rounded-md bg-rose-600 text-white disabled:opacity-50"
                      >
                        {busyId === item.id ? "Deleting..." : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {error ? <p className="px-4 py-3 text-sm text-rose-600">{error}</p> : null}
    </div>
  );
}
