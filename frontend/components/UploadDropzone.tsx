"use client";

import { useRef, useState } from "react";

import { uploadDocument } from "@/lib/api";

const allowedTypes = ["application/pdf", "image/jpeg", "image/jpg", "image/png"];

export function UploadDropzone({ onUploaded }: { onUploaded: (id: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [selected, setSelected] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const processFile = async (file: File) => {
    if (!allowedTypes.includes(file.type)) {
      setMessage("Unsupported file type. Use PDF/JPG/JPEG/PNG.");
      return;
    }

    setSelected(file);
    setUploading(true);
    setMessage("Uploading and starting processing...");
    try {
      const created = await uploadDocument(file);
      setMessage("Upload successful.");
      onUploaded(created.id);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="panel p-6 animate-rise">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) {
            void processFile(file);
          }
        }}
        className={`border-2 border-dashed rounded-2xl p-8 text-center transition ${
          dragging ? "border-emerald-700 bg-emerald-50" : "border-slate-300"
        }`}
      >
        <p className="text-lg font-semibold">Upload Document</p>
        <p className="text-sm text-slate-600 mt-2">Drop PDF/JPG/JPEG/PNG here or click to browse</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-5 px-4 py-2 bg-ink text-white rounded-lg"
          disabled={uploading}
        >
          {uploading ? "Uploading..." : "Choose File"}
        </button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              void processFile(file);
            }
          }}
        />
      </div>
      {selected ? <p className="text-sm mt-3 text-slate-700">Selected: {selected.name}</p> : null}
      {message ? <p className="text-sm mt-2 text-slate-700">{message}</p> : null}
    </div>
  );
}
