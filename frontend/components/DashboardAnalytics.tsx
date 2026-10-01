import { DocumentItem, ProcessingStatus } from "@/types/document";

const statusStyles: Record<ProcessingStatus, string> = {
  UPLOADED: "bg-sky-100 text-sky-800",
  PROCESSING: "bg-amber-100 text-amber-800",
  COMPLETED: "bg-emerald-100 text-emerald-800",
  REVIEW_REQUIRED: "bg-orange-100 text-orange-800",
  FAILED: "bg-rose-100 text-rose-800",
  REVIEWED: "bg-indigo-100 text-indigo-800",
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function safePercent(part: number, total: number): number {
  if (!total) return 0;
  return (part / total) * 100;
}

export function DashboardAnalytics({ items }: { items: DocumentItem[] }) {
  const totalDocs = items.length;

  const statusCounts: Record<ProcessingStatus, number> = {
    UPLOADED: 0,
    PROCESSING: 0,
    COMPLETED: 0,
    REVIEW_REQUIRED: 0,
    FAILED: 0,
    REVIEWED: 0,
  };

  const typeCounts = new Map<string, number>();
  let totalProcessingMs = 0;
  let processingSamples = 0;
  let correctedCount = 0;

  for (const doc of items) {
    statusCounts[doc.processing_status] += 1;

    const typeKey = doc.document_type || "other";
    typeCounts.set(typeKey, (typeCounts.get(typeKey) || 0) + 1);

    const timeMs = doc.ocr_result?.processing_time_ms;
    if (typeof timeMs === "number") {
      totalProcessingMs += timeMs;
      processingSamples += 1;
    }

    const ex = doc.extracted_data;
    if (
      ex &&
      (ex.document_number_corrected ||
        ex.vendor_corrected ||
        ex.document_date_corrected ||
        ex.total_amount_corrected !== null ||
        ex.tax_amount_corrected !== null ||
        ex.currency_corrected)
    ) {
      correctedCount += 1;
    }
  }

  const completedRate = safePercent(statusCounts.COMPLETED + statusCounts.REVIEWED, totalDocs);
  const failureRate = safePercent(statusCounts.FAILED, totalDocs);
  const correctionRate = safePercent(correctedCount, totalDocs);
  const avgProcessingMs = processingSamples ? Math.round(totalProcessingMs / processingSamples) : 0;

  const topTypes = Array.from(typeCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);

  return (
    <section className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <article className="panel p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500">Total Documents</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{totalDocs}</p>
          <p className="text-sm text-slate-600 mt-1">Total uploads processed by the portal.</p>
        </article>

        <article className="panel p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500">Completion Rate</p>
          <p className="mt-2 text-3xl font-bold text-emerald-700">{completedRate.toFixed(1)}%</p>
          <p className="text-sm text-slate-600 mt-1">Completed + reviewed vs total documents.</p>
        </article>

        <article className="panel p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500">Failure Rate</p>
          <p className="mt-2 text-3xl font-bold text-rose-700">{failureRate.toFixed(1)}%</p>
          <p className="text-sm text-slate-600 mt-1">Documents failed in OCR/extraction pipeline.</p>
        </article>

        <article className="panel p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500">Avg OCR Time</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {avgProcessingMs ? formatDuration(avgProcessingMs) : "-"}
          </p>
          <p className="text-sm text-slate-600 mt-1">Average OCR processing time from saved results.</p>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="panel p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Processing Breakdown</h3>
            <span className="text-sm text-slate-500">Correction Rate: {correctionRate.toFixed(1)}%</span>
          </div>

          <div className="space-y-3">
            {(Object.keys(statusCounts) as ProcessingStatus[]).map((status) => {
              const count = statusCounts[status];
              const width = safePercent(count, totalDocs);
              return (
                <div key={status} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className={`inline-flex px-2 py-1 rounded-full text-xs font-semibold ${statusStyles[status]}`}>
                      {status}
                    </span>
                    <span className="text-slate-700">{count}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full bg-slate-900" style={{ width: `${width}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </article>

        <article className="panel p-5 space-y-4">
          <h3 className="text-lg font-semibold">Document Type Distribution</h3>
          {topTypes.length ? (
            <div className="space-y-3">
              {topTypes.map(([name, count]) => {
                const width = safePercent(count, totalDocs);
                return (
                  <div key={name} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-800 capitalize">{name.replaceAll("_", " ")}</span>
                      <span className="text-slate-600">{count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div className="h-full bg-emerald-700" style={{ width: `${width}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-600">No classified documents yet.</p>
          )}
        </article>
      </div>
    </section>
  );
}
