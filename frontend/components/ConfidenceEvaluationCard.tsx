import { DocumentItem } from "@/types/document";

function toLabel(name: string): string {
  if (name === "total_amount") return "Total";
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatPercent(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function ConfidenceEvaluationCard({ document }: { document: DocumentItem }) {
  const evaluation = document.extracted_data?.confidence_data?.evaluation;

  if (!evaluation) {
    return (
      <section className="panel p-4 space-y-2">
        <h3 className="text-lg font-semibold">Confidence Evaluation</h3>
        <p className="text-sm text-slate-600">Evaluation will appear after extraction is completed.</p>
      </section>
    );
  }

  const isAccept = evaluation.decision === "ACCEPT";

  return (
    <section className="panel p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-lg font-semibold">Confidence Evaluation</h3>
        <span
          className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold ${
            isAccept ? "bg-emerald-100 text-emerald-800" : "bg-orange-100 text-orange-800"
          }`}
        >
          {isAccept ? "ACCEPT" : "REVIEW"}
        </span>
      </div>

      <div className="grid md:grid-cols-3 gap-3 text-sm">
        <div className="rounded-lg border border-slate-200 p-3">
          <p className="text-slate-500">Overall Confidence</p>
          <p className="text-xl font-semibold text-slate-900">{formatPercent(evaluation.overall_score)}</p>
        </div>
        <div className="rounded-lg border border-slate-200 p-3">
          <p className="text-slate-500">Accept Threshold</p>
          <p className="text-xl font-semibold text-slate-900">{formatPercent(evaluation.threshold)}</p>
        </div>
        <div className="rounded-lg border border-slate-200 p-3">
          <p className="text-slate-500">Validation Anomalies</p>
          <p className="text-xl font-semibold text-slate-900">{evaluation.anomaly_count}</p>
        </div>
      </div>

      {!isAccept ? (
        <div className="space-y-3 text-sm">
          <div>
            <p className="font-medium text-slate-900">Review Reasons</p>
            <p className="text-slate-600">{evaluation.reasons.map(toLabel).join(", ") || "-"}</p>
          </div>
          <div>
            <p className="font-medium text-slate-900">Missing Critical Fields</p>
            <p className="text-slate-600">
              {evaluation.missing_critical_fields.length
                ? evaluation.missing_critical_fields.map(toLabel).join(", ")
                : "-"}
            </p>
          </div>
        </div>
      ) : null}
    </section>
  );
}
