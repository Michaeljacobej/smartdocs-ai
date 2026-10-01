"use client";

import { useMemo, useState } from "react";

import { updateExtractedData } from "@/lib/api";
import { CorrectionPayload, DocumentItem } from "@/types/document";

function parseNumber(input: string): number | null {
  if (!input.trim()) return null;
  const parsed = Number(input);
  return Number.isFinite(parsed) ? parsed : null;
}

export function ExtractedDataForm({ document, onSaved }: { document: DocumentItem; onSaved: () => void }) {
  const data = document.extracted_data;
  const initial = useMemo<CorrectionPayload>(
    () => ({
      document_number: data?.document_number_corrected ?? data?.document_number_original ?? null,
      vendor: data?.vendor_corrected ?? data?.vendor_original ?? null,
      document_date: data?.document_date_corrected ?? data?.document_date_original ?? null,
      total_amount: data?.total_amount_corrected ?? data?.total_amount_original ?? null,
      tax_amount: data?.tax_amount_corrected ?? data?.tax_amount_original ?? null,
      currency: data?.currency_corrected ?? data?.currency_original ?? null,
    }),
    [data],
  );

  const [form, setForm] = useState({
    document_number: initial.document_number ?? "",
    vendor: initial.vendor ?? "",
    document_date: initial.document_date ?? "",
    total_amount: initial.total_amount?.toString() ?? "",
    tax_amount: initial.tax_amount?.toString() ?? "",
    currency: initial.currency ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    try {
      setSaving(true);
      setError(null);
      const payload: CorrectionPayload = {
        document_number: form.document_number || null,
        vendor: form.vendor || null,
        document_date: form.document_date || null,
        total_amount: parseNumber(form.total_amount),
        tax_amount: parseNumber(form.tax_amount),
        currency: form.currency ? form.currency.toUpperCase() : null,
      };
      await updateExtractedData(document.id, payload);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save correction");
    } finally {
      setSaving(false);
    }
  };

  const rows = [
    {
      key: "document_number",
      label: "Document Number",
      original: data?.document_number_original || "-",
      corrected: data?.document_number_corrected || "-",
    },
    { key: "vendor", label: "Vendor", original: data?.vendor_original || "-", corrected: data?.vendor_corrected || "-" },
    {
      key: "document_date",
      label: "Document Date",
      original: data?.document_date_original || "-",
      corrected: data?.document_date_corrected || "-",
    },
    {
      key: "total_amount",
      label: "Total",
      original: data?.total_amount_original?.toString() || "-",
      corrected: data?.total_amount_corrected?.toString() || "-",
    },
    {
      key: "tax_amount",
      label: "Tax Amount",
      original: data?.tax_amount_original?.toString() || "-",
      corrected: data?.tax_amount_corrected?.toString() || "-",
    },
    {
      key: "currency",
      label: "Currency",
      original: data?.currency_original || "-",
      corrected: data?.currency_corrected || "-",
    },
  ];

  const fieldConfidences = data?.confidence_data?.field_confidences ?? {};

  const formatConfidence = (value: number | undefined) => {
    if (value === undefined || Number.isNaN(value)) return "-";
    return `${Math.round(value * 100)}%`;
  };

  return (
    <div className="panel p-4 space-y-4">
      <h3 className="text-lg font-semibold">Extracted Information</h3>
      <div className="overflow-auto">
        <table className="w-full text-sm min-w-[720px]">
          <thead>
            <tr className="text-left text-slate-600 border-b border-slate-200">
              <th className="py-2">Field</th>
              <th className="py-2">Original Value</th>
              <th className="py-2">Corrected Value</th>
              <th className="py-2">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-b border-slate-100">
                <td className="py-2 font-medium">{row.label}</td>
                <td className="py-2 text-slate-600">{row.original}</td>
                <td className="py-2 text-slate-900">{row.corrected}</td>
                <td className="py-2 text-slate-700">{formatConfidence(fieldConfidences[row.key])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        <input className="border border-slate-300 rounded-lg p-2" placeholder="Document Number" value={form.document_number} onChange={(e) => setForm((s) => ({ ...s, document_number: e.target.value }))} />
        <input className="border border-slate-300 rounded-lg p-2" placeholder="Vendor" value={form.vendor} onChange={(e) => setForm((s) => ({ ...s, vendor: e.target.value }))} />
        <input className="border border-slate-300 rounded-lg p-2" placeholder="YYYY-MM-DD" value={form.document_date} onChange={(e) => setForm((s) => ({ ...s, document_date: e.target.value }))} />
        <input className="border border-slate-300 rounded-lg p-2" placeholder="Currency (e.g. IDR)" value={form.currency} onChange={(e) => setForm((s) => ({ ...s, currency: e.target.value }))} />
        <input className="border border-slate-300 rounded-lg p-2" placeholder="Total" value={form.total_amount} onChange={(e) => setForm((s) => ({ ...s, total_amount: e.target.value }))} />
        <input className="border border-slate-300 rounded-lg p-2" placeholder="Tax Amount" value={form.tax_amount} onChange={(e) => setForm((s) => ({ ...s, tax_amount: e.target.value }))} />
      </div>

      <div className="flex items-center gap-3">
        <button onClick={() => void save()} disabled={saving} className="px-4 py-2 rounded-lg bg-emerald-700 text-white disabled:opacity-60">
          {saving ? "Saving..." : "Save Correction"}
        </button>
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      </div>
    </div>
  );
}
