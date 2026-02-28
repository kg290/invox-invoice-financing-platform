"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useState, useCallback, useRef, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, ArrowLeft, Loader2, Check, Upload, Image, X,
  AlertCircle, CheckCircle, Clock, Eye, RefreshCw,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";

type OcrStatus = "idle" | "uploading" | "processing" | "done" | "failed";

interface CreatedInvoice {
  id: number;
  invoice_number: string;
  ocr_status: string;
  grand_total: number;
  buyer_name: string;
  invoice_date: string;
}

export default function CreateInvoicePage() {
  const params = useParams();
  const vendorId = params.id as string;
  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [status, setStatus] = useState<OcrStatus>("idle");
  const [createdInvoice, setCreatedInvoice] = useState<CreatedInvoice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
  const MAX_SIZE = 15 * 1024 * 1024;

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleFile = useCallback((f: File) => {
    if (!ACCEPTED_TYPES.includes(f.type)) {
      toast.error("Only JPEG, PNG, WebP, and PDF files are allowed");
      return;
    }
    if (f.size > MAX_SIZE) {
      toast.error("File must be under 15 MB");
      return;
    }
    setFile(f);
    setError(null);
    setCreatedInvoice(null);
    setStatus("idle");
    if (f.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target?.result as string);
      reader.readAsDataURL(f);
    } else {
      setPreview(null);
    }
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  }, [handleFile]);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const onDragLeave = useCallback(() => setDragActive(false), []);

  const pollOcrStatus = (invoiceId: number) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await api.get(`/invoices/${invoiceId}`);
        const inv = res.data;
        if (inv.ocr_status === "ocr_done") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setStatus("done");
          setCreatedInvoice({
            id: inv.id,
            invoice_number: inv.invoice_number,
            ocr_status: inv.ocr_status,
            grand_total: inv.grand_total || 0,
            buyer_name: inv.buyer_name || "—",
            invoice_date: inv.invoice_date || "—",
          });
          toast.success("OCR completed! Invoice data extracted successfully.");
        } else if (inv.ocr_status === "failed") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setStatus("failed");
          setError("OCR processing failed. Try uploading a clearer image.");
        }
      } catch {
        // keep polling
      }
    }, 2000);
  };

  const uploadInvoice = async () => {
    if (!file) return;
    setStatus("uploading");
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post(`/invoices/ocr-upload/${vendorId}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setStatus("processing");
      toast.success("Invoice uploaded! OCR is processing...");
      setCreatedInvoice({
        id: res.data.invoice_id,
        invoice_number: res.data.invoice_number,
        ocr_status: "processing",
        grand_total: 0,
        buyer_name: "—",
        invoice_date: "—",
      });
      pollOcrStatus(res.data.invoice_id);
    } catch (err: unknown) {
      setStatus("failed");
      setError(getErrorMessage(err, "Upload failed"));
      toast.error(getErrorMessage(err, "Upload failed"));
    }
  };

  const resetForm = () => {
    setFile(null);
    setPreview(null);
    setStatus("idle");
    setCreatedInvoice(null);
    setError(null);
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-14">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">Invo<span className="text-blue-600">X</span></span>
          </Link>
          <Link href={`/vendor/${vendorId}/invoices`} className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> Invoices
          </Link>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-gray-900">Upload Invoice for OCR</h1>
          <p className="text-sm text-gray-500 mt-1">Upload a photo or scan of your invoice. Our AI will automatically extract all details using OCR.</p>
        </div>

        {/* OCR Info Banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <strong>Why OCR?</strong> To prevent fraud, all invoices must be uploaded via OCR scan. Our system verifies the document,
            extracts GST details automatically, and records it on the blockchain. Manually created invoices cannot be listed on the marketplace.
          </div>
        </div>

        {/* Upload Area */}
        {status === "idle" || status === "failed" ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-8 mb-6">
            <div
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                dragActive
                  ? "border-blue-500 bg-blue-50"
                  : file
                  ? "border-green-300 bg-green-50/50"
                  : "border-gray-200 hover:border-blue-300 hover:bg-blue-50/30"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".jpg,.jpeg,.png,.webp,.pdf"
                className="hidden"
                onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }}
              />
              {file ? (
                <div className="space-y-3">
                  {preview ? (
                    <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded-lg shadow-md" />
                  ) : (
                    <div className="w-20 h-20 mx-auto bg-red-50 rounded-xl flex items-center justify-center">
                      <FileText className="w-10 h-10 text-red-500" />
                    </div>
                  )}
                  <p className="text-sm font-semibold text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(0)} KB · {file.type}</p>
                  <button onClick={(e) => { e.stopPropagation(); resetForm(); }}
                    className="inline-flex items-center gap-1 text-xs text-red-600 hover:text-red-800 font-medium">
                    <X className="w-3 h-3" /> Remove & choose another
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-16 h-16 mx-auto bg-gray-50 rounded-2xl flex items-center justify-center">
                    <Upload className="w-8 h-8 text-gray-300" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-700">Drop your invoice here or click to browse</p>
                    <p className="text-xs text-gray-400 mt-1">Supports JPEG, PNG, WebP, PDF · Max 15 MB</p>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {file && (
              <div className="mt-6 flex justify-center">
                <button onClick={uploadInvoice}
                  className="inline-flex items-center gap-2 px-8 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-200">
                  <Upload className="w-5 h-5" /> Upload & Start OCR
                </button>
              </div>
            )}
          </div>
        ) : null}

        {/* Processing State */}
        {(status === "uploading" || status === "processing") && (
          <div className="bg-white rounded-2xl border border-blue-100 p-12 text-center mb-6">
            <div className="w-20 h-20 mx-auto bg-blue-50 rounded-2xl flex items-center justify-center mb-4">
              <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {status === "uploading" ? "Uploading Invoice..." : "OCR Processing..."}
            </h3>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              {status === "uploading"
                ? "Uploading your invoice to the server..."
                : "Our AI is reading your invoice and extracting GST details, buyer info, line items, and amounts. This usually takes 5–15 seconds."}
            </p>
            {/* Progress steps */}
            <div className="mt-6 flex items-center justify-center gap-8 text-xs">
              <div className="flex items-center gap-1.5 text-green-600">
                <CheckCircle className="w-4 h-4" /> Uploaded
              </div>
              <div className={`flex items-center gap-1.5 ${status === "processing" ? "text-blue-600" : "text-gray-300"}`}>
                <Clock className="w-4 h-4" /> OCR Running
              </div>
              <div className="flex items-center gap-1.5 text-gray-300">
                <Check className="w-4 h-4" /> Complete
              </div>
            </div>
          </div>
        )}

        {/* Success State */}
        {status === "done" && createdInvoice && (
          <div className="bg-white rounded-2xl border border-green-100 p-8 mb-6">
            <div className="text-center mb-6">
              <div className="w-16 h-16 mx-auto bg-green-50 rounded-2xl flex items-center justify-center mb-3">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-lg font-bold text-green-800">Invoice Uploaded & OCR Complete!</h3>
              <p className="text-sm text-gray-500 mt-1">Your invoice has been processed and is ready for review.</p>
            </div>

            {/* Extracted summary */}
            <div className="bg-green-50/50 rounded-xl border border-green-100 p-5 mb-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-xs text-gray-400 uppercase font-medium">Invoice #</p>
                  <p className="font-bold text-gray-900 mt-0.5">{createdInvoice.invoice_number}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase font-medium">Buyer</p>
                  <p className="font-semibold text-gray-900 mt-0.5">{createdInvoice.buyer_name}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase font-medium">Date</p>
                  <p className="font-semibold text-gray-900 mt-0.5">{createdInvoice.invoice_date}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase font-medium">Total</p>
                  <p className="font-bold text-green-700 mt-0.5">₹{createdInvoice.grand_total.toLocaleString("en-IN")}</p>
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button onClick={() => router.push(`/vendor/${vendorId}/invoices/${createdInvoice.id}`)}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors">
                <Eye className="w-5 h-5" /> View & List on Marketplace
              </button>
              <button onClick={resetForm}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-50 transition-colors">
                <RefreshCw className="w-5 h-5" /> Upload Another Invoice
              </button>
            </div>
          </div>
        )}

        {/* Blockchain Notice */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 flex items-start gap-3">
          <Image className="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-indigo-800">
            <strong>Blockchain Secured:</strong> Once OCR extracts your invoice data, it is hashed and recorded on the InvoX blockchain.
            This ensures immutability — any tampering will be detectable. Only OCR-verified invoices can be listed on the financing marketplace.
          </div>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
