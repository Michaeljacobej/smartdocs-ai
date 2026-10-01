import { ProcessingStatus as Status } from "@/types/document";

const statusMap: Record<Status, { label: string; color: string; message: string }> = {
  UPLOADED: {
    label: "Uploaded",
    color: "bg-sky-100 text-sky-800",
    message: "File uploaded and waiting to be processed.",
  },
  PROCESSING: {
    label: "Processing",
    color: "bg-amber-100 text-amber-800",
    message: "Document is being processed...",
  },
  COMPLETED: {
    label: "Completed",
    color: "bg-emerald-100 text-emerald-800",
    message: "OCR and extraction completed.",
  },
  REVIEW_REQUIRED: {
    label: "Review Required",
    color: "bg-orange-100 text-orange-800",
    message: "Low confidence or anomalies detected, human review required.",
  },
  FAILED: {
    label: "Failed",
    color: "bg-rose-100 text-rose-800",
    message: "Processing failed.",
  },
  REVIEWED: {
    label: "Reviewed",
    color: "bg-indigo-100 text-indigo-800",
    message: "User corrections were saved.",
  },
};

export function ProcessingStatus({ status }: { status: Status }) {
  const state = statusMap[status];
  return (
    <div className="space-y-1">
      <span className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold ${state.color}`}>
        {state.label}
      </span>
      <p className="text-xs text-slate-600">{state.message}</p>
    </div>
  );
}
