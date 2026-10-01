export type ProcessingStatus =
  | "UPLOADED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "REVIEW_REQUIRED"
  | "REVIEWED";

export interface OCRResult {
  id: string;
  raw_text: string | null;
  processing_status: ProcessingStatus;
  processing_time_ms: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractedData {
  id: string;
  document_number_original: string | null;
  document_number_corrected: string | null;
  vendor_original: string | null;
  vendor_corrected: string | null;
  document_date_original: string | null;
  document_date_corrected: string | null;
  total_amount_original: number | null;
  total_amount_corrected: number | null;
  tax_amount_original: number | null;
  tax_amount_corrected: number | null;
  currency_original: string | null;
  currency_corrected: string | null;
  confidence_data: ExtractionConfidenceData | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractionConfidenceData {
  anomalies?: Array<{ type: string; message: string }>;
  ocr_lines?: Array<{ text: string; confidence: number | null }>;
  field_confidences?: Record<string, number>;
  evaluation?: {
    decision: "ACCEPT" | "REVIEW";
    overall_score: number;
    threshold: number;
    anomaly_count: number;
    missing_critical_fields: string[];
    reasons: string[];
  };
}

export interface Summary {
  id: string;
  summary_text: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  file_name: string;
  mime_type: string;
  file_size: number;
  document_type: string | null;
  processing_status: ProcessingStatus;
  upload_date: string;
  created_at: string;
  updated_at: string;
  ocr_result: OCRResult | null;
  extracted_data: ExtractedData | null;
  summary: Summary | null;
}

export interface DocumentListResponse {
  items: DocumentItem[];
}

export interface CorrectionPayload {
  document_number: string | null;
  vendor: string | null;
  document_date: string | null;
  total_amount: number | null;
  tax_amount: number | null;
  currency: string | null;
}
