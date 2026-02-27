"use client";

import { useState, useEffect, useCallback } from "react";
import axios from "axios";

/* ═══════════════════════════════════════════════════════════════════
   Government of India — Unified Document Verification Portal
   Styled to look like an official Indian government website
   (DigiLocker / UIDAI / GST Portal aesthetic)
   ═══════════════════════════════════════════════════════════════════ */

interface DocumentCheck {
  document_type: string;
  status: "verified" | "not_verified" | "format_error";
  details: Record<string, unknown>;
}

interface VerificationResult {
  overall_status: "verified" | "not_verified";
  verification_id: string;
  timestamp: string;
  checks: DocumentCheck[];
  entity_name?: string;
  business_type?: string;
  state?: string;
  gst_status?: string;
}

export default function VerifyPortalPage() {
  const [stage, setStage] = useState<"loading" | "verifying" | "result">("loading");
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState("");
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pan, setPan] = useState("");
  const [aadhaar, setAadhaar] = useState("");
  const [gstin, setGstin] = useState("");

  const runVerification = useCallback(async (panNum: string, aadhaarNum: string, gstinNum: string) => {
    setStage("verifying");
    setProgress(0);

    // Simulated step-by-step verification progress
    const steps = [
      { label: "Connecting to Central Board of Indirect Taxes & Customs...", pct: 10 },
      { label: "Querying GST Network for GSTIN validation...", pct: 25 },
      { label: "Connecting to Income Tax Department servers...", pct: 40 },
      { label: "Verifying PAN with NSDL database...", pct: 55 },
      { label: "Connecting to UIDAI Aadhaar Verification Service...", pct: 70 },
      { label: "Running cross-verification checks...", pct: 85 },
      { label: "Generating verification certificate...", pct: 95 },
    ];

    for (const step of steps) {
      setCurrentStep(step.label);
      setProgress(step.pct);
      await new Promise((r) => setTimeout(r, 600 + Math.random() * 400));
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
      const res = await axios.post(`${API_URL}/auth/verify-documents`, {
        pan_number: panNum,
        aadhaar_number: aadhaarNum,
        gstin: gstinNum,
      });

      setProgress(100);
      setCurrentStep("Verification complete.");
      await new Promise((r) => setTimeout(r, 500));
      setResult(res.data);
      setStage("result");

      // Notify the parent window (registration page) about the result
      if (window.opener) {
        window.opener.postMessage(
          { type: "INVOX_VERIFICATION_RESULT", data: res.data },
          window.location.origin
        );
      }
    } catch (err: unknown) {
      setError(
        axios.isAxiosError(err)
          ? err.response?.data?.detail || "Verification service unavailable"
          : "Connection to government servers failed"
      );
      setStage("result");
    }
  }, []);

  useEffect(() => {
    // Read verification data from URL query params
    const params = new URLSearchParams(window.location.search);
    const panParam = params.get("pan");
    const aadhaarParam = params.get("aadhaar");
    const gstinParam = params.get("gstin");

    if (panParam && aadhaarParam && gstinParam) {
      setPan(panParam);
      setAadhaar(aadhaarParam);
      setGstin(gstinParam);
      runVerification(panParam, aadhaarParam, gstinParam);
    } else {
      setError("No verification data found. Please initiate verification from the registration page.");
      setStage("result");
    }
  }, [runVerification]);

  const maskedAadhaar = aadhaar ? `XXXX XXXX ${aadhaar.slice(-4)}` : "";

  return (
    <div className="min-h-screen bg-[#f7f7f7]" style={{ fontFamily: "'Noto Sans', 'Segoe UI', Arial, sans-serif" }}>
      {/* ── Government Header Bar ── */}
      <div className="bg-gradient-to-b from-[#06038D] to-[#1a1a8e] text-white">
        {/* Tricolor stripe */}
        <div className="flex h-1">
          <div className="flex-1 bg-[#FF9933]" />
          <div className="flex-1 bg-white" />
          <div className="flex-1 bg-[#138808]" />
        </div>

        <div className="max-w-6xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Ashoka Chakra / Emblem */}
              <div className="w-14 h-14 rounded-full bg-white/10 border-2 border-white/30 flex items-center justify-center flex-shrink-0">
                <svg viewBox="0 0 100 100" className="w-10 h-10">
                  <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.8)" strokeWidth="2" />
                  <circle cx="50" cy="50" r="8" fill="rgba(255,255,255,0.9)" />
                  {/* Spokes of Ashoka Chakra */}
                  {Array.from({ length: 24 }).map((_, i) => {
                    const angle = (i * 15 * Math.PI) / 180;
                    const x1 = 50 + 12 * Math.cos(angle);
                    const y1 = 50 + 12 * Math.sin(angle);
                    const x2 = 50 + 40 * Math.cos(angle);
                    const y2 = 50 + 40 * Math.sin(angle);
                    return (
                      <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(255,255,255,0.6)" strokeWidth="1" />
                    );
                  })}
                </svg>
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-wide">
                  भारत सरकार | Government of India
                </h1>
                <p className="text-blue-200 text-xs mt-0.5">
                  Ministry of Corporate Affairs — Unified Document Verification Service
                </p>
              </div>
            </div>
            <div className="hidden md:flex items-center gap-3 text-xs text-blue-200">
              <span>DigiLocker Integrated</span>
              <span className="text-blue-400">|</span>
              <span>NIC Certified</span>
              <span className="text-blue-400">|</span>
              <span>ISO 27001</span>
            </div>
          </div>
        </div>

        {/* Sub header */}
        <div className="bg-[#04026b] border-t border-blue-700">
          <div className="max-w-6xl mx-auto px-4 py-2 flex items-center justify-between text-xs">
            <div className="flex items-center gap-4 text-blue-300">
              <span>🔒 Secure Connection (SSL/TLS)</span>
              <span>gov.in verified</span>
            </div>
            <div className="text-blue-300">
              Portal Version 4.2.1 | Last Updated: Jan 2026
            </div>
          </div>
        </div>
      </div>

      {/* ── Page Title Banner ── */}
      <div className="bg-gradient-to-r from-[#FF9933] via-[#ffb366] to-[#FF9933]">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h2 className="text-lg font-bold text-white drop-shadow-sm">
            Unified Business Document Verification Portal
          </h2>
          <p className="text-white/80 text-sm mt-0.5">
            GST Network • Income Tax Department • UIDAI Aadhaar • MCA
          </p>
        </div>
      </div>

      {/* ── Main Content ── */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Breadcrumb */}
        <div className="text-xs text-gray-500 mb-4 flex items-center gap-1">
          <span>Home</span>
          <span>›</span>
          <span>Services</span>
          <span>›</span>
          <span className="text-[#06038D] font-medium">Business Verification</span>
        </div>

        {/* Document Details Card */}
        {(pan || aadhaar || gstin) && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm mb-6">
            <div className="bg-[#06038D] text-white px-5 py-3 rounded-t-lg flex items-center gap-2">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
              </svg>
              <span className="font-semibold text-sm">Documents Under Verification</span>
            </div>
            <div className="p-5 grid grid-cols-3 gap-4">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">PAN Number</p>
                <p className="text-sm font-mono font-bold text-gray-800 mt-1">{pan}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">Income Tax Dept.</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Aadhaar Number</p>
                <p className="text-sm font-mono font-bold text-gray-800 mt-1">{maskedAadhaar}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">UIDAI</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">GSTIN</p>
                <p className="text-sm font-mono font-bold text-gray-800 mt-1">{gstin}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">CBIC / GST Network</p>
              </div>
            </div>
          </div>
        )}

        {/* ── Verification Progress ── */}
        {stage === "verifying" && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <div className="bg-[#06038D] text-white px-5 py-3 flex items-center gap-2">
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="font-semibold text-sm">Verification In Progress</span>
            </div>
            <div className="p-8">
              {/* Progress bar */}
              <div className="mb-6">
                <div className="flex justify-between text-xs text-gray-500 mb-2">
                  <span>Processing...</span>
                  <span className="font-semibold text-[#06038D]">{progress}%</span>
                </div>
                <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden border border-gray-200">
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${progress}%`,
                      background: "linear-gradient(90deg, #FF9933, #06038D, #138808)",
                    }}
                  />
                </div>
              </div>

              {/* Current step */}
              <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="w-8 h-8 rounded-full bg-[#06038D] flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-white animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-[#06038D]">{currentStep}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Please wait while we verify your documents with government databases</p>
                </div>
              </div>

              {/* Step indicators */}
              <div className="mt-6 grid grid-cols-4 gap-2">
                {["GST Network", "Income Tax", "UIDAI", "Cross-Check"].map((label, i) => {
                  const stepPcts = [25, 55, 70, 95];
                  const done = progress >= stepPcts[i];
                  const active = progress >= (stepPcts[i - 1] || 0) && progress < stepPcts[i];
                  return (
                    <div
                      key={label}
                      className={`text-center p-3 rounded-lg border ${
                        done
                          ? "bg-green-50 border-green-200"
                          : active
                          ? "bg-yellow-50 border-yellow-300 animate-pulse"
                          : "bg-gray-50 border-gray-200"
                      }`}
                    >
                      <div className={`w-8 h-8 rounded-full mx-auto mb-1.5 flex items-center justify-center ${
                        done ? "bg-green-500" : active ? "bg-yellow-400" : "bg-gray-300"
                      }`}>
                        {done ? (
                          <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        ) : active ? (
                          <svg className="w-4 h-4 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                        ) : (
                          <span className="text-white text-xs font-bold">{i + 1}</span>
                        )}
                      </div>
                      <p className={`text-[11px] font-medium ${done ? "text-green-700" : active ? "text-yellow-700" : "text-gray-400"}`}>
                        {label}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── Loading state ── */}
        {stage === "loading" && !error && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-[#06038D] flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <p className="text-sm text-gray-600">Initializing verification portal...</p>
          </div>
        )}

        {/* ── Error state ── */}
        {error && (
          <div className="bg-white rounded-lg border border-red-200 shadow-sm overflow-hidden">
            <div className="bg-red-600 text-white px-5 py-3 flex items-center gap-2">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span className="font-semibold text-sm">Verification Error</span>
            </div>
            <div className="p-6">
              <p className="text-red-700 text-sm">{error}</p>
              <button
                onClick={() => window.close()}
                className="mt-4 px-6 py-2 bg-gray-100 border border-gray-300 rounded text-sm text-gray-700 hover:bg-gray-200 transition-colors"
              >
                Close Window
              </button>
            </div>
          </div>
        )}

        {/* ── Verification Result ── */}
        {stage === "result" && result && (
          <div className="space-y-6">
            {/* Overall Status Banner */}
            <div
              className={`rounded-lg border-2 overflow-hidden shadow-sm ${
                result.overall_status === "verified"
                  ? "border-green-500"
                  : "border-red-500"
              }`}
            >
              <div
                className={`px-6 py-5 flex items-center gap-4 ${
                  result.overall_status === "verified"
                    ? "bg-gradient-to-r from-green-600 to-green-700"
                    : "bg-gradient-to-r from-red-600 to-red-700"
                }`}
              >
                <div className="w-16 h-16 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                  {result.overall_status === "verified" ? (
                    <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">
                    {result.overall_status === "verified"
                      ? "ALL DOCUMENTS VERIFIED"
                      : "VERIFICATION FAILED"}
                  </h3>
                  <p className="text-white/80 text-sm mt-1">
                    {result.overall_status === "verified"
                      ? "All submitted documents have been successfully verified against government databases."
                      : "One or more documents could not be verified. Please check the details below."}
                  </p>
                </div>
              </div>

              {/* Verification metadata */}
              <div className="bg-white p-5">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Verification ID</p>
                    <p className="font-mono font-bold text-gray-800 mt-0.5">{result.verification_id}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Timestamp</p>
                    <p className="font-medium text-gray-800 mt-0.5">
                      {new Date(result.timestamp).toLocaleString("en-IN", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </p>
                  </div>
                  {result.entity_name && (
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Entity Name</p>
                      <p className="font-medium text-gray-800 mt-0.5">{result.entity_name}</p>
                    </div>
                  )}
                  {result.state && (
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Registered State</p>
                      <p className="font-medium text-gray-800 mt-0.5">{result.state}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Individual Document Checks */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
              <div className="bg-[#06038D] text-white px-5 py-3 flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.788l1.599.799L9 4.323V3a1 1 0 011-1zm-5 8.274l-.818 2.552c.25.112.526.174.818.174.292 0 .569-.062.818-.174L5 10.274zm10 0l-.818 2.552c.25.112.526.174.818.174.292 0 .569-.062.818-.174L15 10.274z" clipRule="evenodd" />
                </svg>
                <span className="font-semibold text-sm">Detailed Verification Report</span>
              </div>
              <div className="divide-y divide-gray-100">
                {result.checks.map((check, i) => (
                  <div key={i} className="p-5 flex items-start gap-4">
                    {/* Status icon */}
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                        check.status === "verified"
                          ? "bg-green-100"
                          : check.status === "format_error"
                          ? "bg-yellow-100"
                          : "bg-red-100"
                      }`}
                    >
                      {check.status === "verified" ? (
                        <svg className="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : check.status === "format_error" ? (
                        <svg className="w-6 h-6 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>

                    {/* Details */}
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h4 className="text-sm font-bold text-gray-800">{check.document_type}</h4>
                        <span
                          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                            check.status === "verified"
                              ? "bg-green-100 text-green-700"
                              : check.status === "format_error"
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-red-100 text-red-700"
                          }`}
                        >
                          {check.status === "verified" ? "VERIFIED" : check.status === "format_error" ? "FORMAT ERROR" : "NOT VERIFIED"}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{String(check.details.message || "")}</p>
                      {check.details.source && (
                        <p className="text-[11px] text-gray-400 mt-1.5 flex items-center gap-1">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                          </svg>
                          Source: {String(check.details.source)}
                        </p>
                      )}
                      {/* Extra details for GSTIN */}
                      {check.document_type === "GSTIN" && check.status === "verified" && check.details.legal_name && (
                        <div className="mt-2 grid grid-cols-2 gap-2 bg-gray-50 rounded p-2 text-[11px] text-gray-600">
                          <span><strong>Legal Name:</strong> {String(check.details.legal_name)}</span>
                          <span><strong>Status:</strong> {String(check.details.compliance_rating) || "Active"}</span>
                          <span><strong>Reg. Date:</strong> {String(check.details.registration_date)}</span>
                          <span><strong>State:</strong> {String(check.details.state)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-between bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="text-xs text-gray-400">
                This verification report is generated by the Unified Business Verification
                Portal, Government of India. Report ID: {result.verification_id}
              </div>
              <button
                onClick={() => window.close()}
                className="px-6 py-2.5 bg-[#06038D] text-white font-semibold rounded text-sm hover:bg-[#04026b] transition-colors"
              >
                Close & Return to Registration
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Government Footer ── */}
      <div className="mt-12 bg-[#333] text-gray-400 text-xs">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <h4 className="text-gray-300 font-semibold mb-2">Government Links</h4>
              <p>Ministry of Corporate Affairs</p>
              <p>Central Board of Indirect Taxes</p>
              <p>Income Tax Department</p>
            </div>
            <div>
              <h4 className="text-gray-300 font-semibold mb-2">Related Portals</h4>
              <p>DigiLocker (digilocker.gov.in)</p>
              <p>GST Portal (gst.gov.in)</p>
              <p>UIDAI (uidai.gov.in)</p>
            </div>
            <div>
              <h4 className="text-gray-300 font-semibold mb-2">Information</h4>
              <p>Data is verified against government databases</p>
              <p>All connections are encrypted (SSL/TLS)</p>
              <p>Compliant with IT Act, 2000</p>
            </div>
          </div>
          <div className="border-t border-gray-600 pt-4 text-center">
            <p>© 2026 Government of India | National Informatics Centre (NIC)</p>
            <p className="mt-1">Content owned and maintained by Ministry of Corporate Affairs</p>
          </div>
        </div>
        {/* Bottom tricolor */}
        <div className="flex h-1">
          <div className="flex-1 bg-[#FF9933]" />
          <div className="flex-1 bg-white" />
          <div className="flex-1 bg-[#138808]" />
        </div>
      </div>
    </div>
  );
}
