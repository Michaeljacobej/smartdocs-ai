import { useState } from "react";

import { documentFileUrl } from "@/lib/api";
import { DocumentItem } from "@/types/document";

export function DocumentPreview({ document }: { document: DocumentItem }) {
  const [previewFailed, setPreviewFailed] = useState(false);
  const url = documentFileUrl(document.id);
  const mimeType = document.mime_type?.toLowerCase() ?? "";
  const fileName = (document.file_name ?? "").toLowerCase();
  const isPdf = mimeType.includes("pdf") || fileName.endsWith(".pdf");

  return (
    <div className="panel p-4 space-y-3">
      <h3 className="text-lg font-semibold">Original Document</h3>

      {!previewFailed ? (
        isPdf ? (
          <object
            key={url}
            data={url}
            type="application/pdf"
            className="w-full h-[520px] rounded-xl border border-slate-200 bg-white"
            onError={() => setPreviewFailed(true)}
          >
            <embed src={url} type="application/pdf" className="w-full h-[520px]" />
          </object>
        ) : (
          <img
            key={url}
            src={url}
            alt={document.file_name}
            onError={() => setPreviewFailed(true)}
            className="max-h-[520px] w-full object-contain rounded-xl border border-slate-200 bg-white"
          />
        )
      ) : (
        <div className="flex h-[520px] items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-500">
          Preview unavailable for this file.
        </div>
      )}
    </div>
  );
}
