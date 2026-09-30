import { documentFileUrl } from "@/lib/api";
import { DocumentItem } from "@/types/document";

export function DocumentPreview({ document }: { document: DocumentItem }) {
  const url = documentFileUrl(document.id);
  const isPdf = document.mime_type === "application/pdf";

  return (
    <div className="panel p-4 space-y-3">
      <h3 className="text-lg font-semibold">Original Document</h3>
      {isPdf ? (
        <iframe src={url} className="w-full h-[520px] rounded-xl border border-slate-200" title="Document PDF" />
      ) : (
        <img src={url} alt={document.file_name} className="max-h-[520px] w-full object-contain rounded-xl border border-slate-200 bg-white" />
      )}
    </div>
  );
}
