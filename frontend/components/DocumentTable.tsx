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

export function DocumentTable({ items, onDeleted }: { items: DocumentItem[]; onDeleted: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

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
      <div className="overflow-auto">
        <table className="w-full text-sm min-w-[900px]">
          <thead className="bg-slate-100 text-slate-700">
            <tr>
              <th className="text-left p-3">File Name</th>
              <th className="text-left p-3">Type</th>
              <th className="text-left p-3">Upload Date</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Total</th>
              <th className="text-left p-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const total = item.extracted_data?.total_amount_corrected ?? item.extracted_data?.total_amount_original ?? null;
              const currency = item.extracted_data?.currency_corrected ?? item.extracted_data?.currency_original ?? null;
              return (
                <tr key={item.id} className="border-t border-slate-200 align-top">
                  <td className="p-3">{item.file_name}</td>
                  <td className="p-3">{item.document_type || "-"}</td>
                  <td className="p-3">{new Date(item.upload_date).toLocaleString()}</td>
                  <td className="p-3"><ProcessingStatus status={item.processing_status} /></td>
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
