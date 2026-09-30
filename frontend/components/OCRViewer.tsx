export function OCRViewer({ text }: { text: string | null }) {
  return (
    <div className="panel p-4 space-y-2">
      <h3 className="text-lg font-semibold">OCR Result</h3>
      <pre className="max-h-72 overflow-auto rounded-xl bg-slate-950 text-slate-100 p-4 text-sm whitespace-pre-wrap">
        {text || "OCR text is not available yet."}
      </pre>
    </div>
  );
}
