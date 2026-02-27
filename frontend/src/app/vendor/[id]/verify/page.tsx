"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, ArrowLeft, Shield, CheckCircle2, XCircle,
  AlertTriangle, Loader2, RefreshCw, Clock,
} from "lucide-react";
import api from "@/lib/api";
import { VerificationCheck } from "@/lib/types";

const CHECK_LABELS: Record<string, string> = {
  gstin: "GST Registration (GSTIN)",
  pan: "PAN Card Verification",
  aadhaar: "Aadhaar Verification",
  bank: "Bank Account Verification",
  cibil: "CIBIL / Credit Score",
  business_age: "Business Maturity",
};

const CHECK_ORDER = ["gstin", "pan", "aadhaar", "bank", "cibil", "business_age"];

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "passed":
      return <CheckCircle2 className="w-5 h-5 text-green-500" />;
    case "failed":
      return <XCircle className="w-5 h-5 text-red-500" />;
    case "warning":
      return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
    default:
      return <Clock className="w-5 h-5 text-gray-400" />;
  }
}

function statusBg(status: string) {
  switch (status) {
    case "passed": return "bg-green-50 border-green-200";
    case "failed": return "bg-red-50 border-red-200";
    case "warning": return "bg-yellow-50 border-yellow-200";
    default: return "bg-gray-50 border-gray-200";
  }
}

export default function VendorVerifyPage() {
  const params = useParams();
  const vendorId = params.id as string;
  const [checks, setChecks] = useState<VerificationCheck[]>([]);
  const [profileStatus, setProfileStatus] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await api.get(`/verification/${vendorId}/status`);
      setChecks(res.data.checks);
      setProfileStatus(res.data.profile_status);
    } catch { /* empty */ }
    setLoaded(true);
  };

  useEffect(() => { fetchStatus(); }, [vendorId]);

  const runVerification = async () => {
    setRunning(true);
    try {
      const res = await api.post(`/verification/${vendorId}/verify`);
      toast.success(res.data.message || "Verification complete");
      await fetchStatus();
    } catch {
      toast.error("Verification failed");
    }
    setRunning(false);
  };

  const sortedChecks = [...checks].sort(
    (a, b) => CHECK_ORDER.indexOf(a.check_type) - CHECK_ORDER.indexOf(b.check_type)
  );

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">
                Invo<span className="text-blue-600">X</span>
              </span>
            </Link>
            <Link href={`/vendor/${vendorId}`} className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1">
              <ArrowLeft className="w-4 h-4" /> Vendor Profile
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Title & Action */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Shield className="w-6 h-6 text-blue-600" /> Vendor Verification
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Automated checks to verify vendor genuineness for lender confidence
            </p>
          </div>
          <button
            onClick={runVerification}
            disabled={running}
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-60 transition-colors"
          >
            {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            {running ? "Running Checks..." : "Run Verification"}
          </button>
        </div>

        {/* Overall Status Banner */}
        {profileStatus && (
          <div className={`rounded-xl border p-4 mb-6 ${
            profileStatus === "verified" ? "bg-green-50 border-green-200" :
            profileStatus === "rejected" ? "bg-red-50 border-red-200" :
            "bg-yellow-50 border-yellow-200"
          }`}>
            <div className="flex items-center gap-3">
              {profileStatus === "verified" && <CheckCircle2 className="w-6 h-6 text-green-600" />}
              {profileStatus === "rejected" && <XCircle className="w-6 h-6 text-red-600" />}
              {profileStatus === "pending" && <Clock className="w-6 h-6 text-yellow-600" />}
              <div>
                <p className="font-semibold text-gray-900">
                  Profile Status: {profileStatus.charAt(0).toUpperCase() + profileStatus.slice(1)}
                </p>
                <p className="text-sm text-gray-600">
                  {profileStatus === "verified" && "All critical checks passed. Vendor is eligible for financing."}
                  {profileStatus === "rejected" && "Critical checks failed. Manual review or data correction needed."}
                  {profileStatus === "pending" && "Verification pending or warnings found. Click 'Run Verification' to check."}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Checks */}
        {!loaded ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : sortedChecks.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-200">
            <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-2">No verification checks run yet</p>
            <p className="text-sm text-gray-400">Click &quot;Run Verification&quot; to verify this vendor&apos;s data</p>
          </div>
        ) : (
          <div className="space-y-4">
            {sortedChecks.map((check) => (
              <div key={check.id} className={`rounded-xl border p-5 ${statusBg(check.status)}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <StatusIcon status={check.status} />
                    <h3 className="font-semibold text-gray-900">
                      {CHECK_LABELS[check.check_type] || check.check_type}
                    </h3>
                  </div>
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                    check.status === "passed" ? "bg-green-100 text-green-700" :
                    check.status === "failed" ? "bg-red-100 text-red-700" :
                    check.status === "warning" ? "bg-yellow-100 text-yellow-700" :
                    "bg-gray-100 text-gray-600"
                  }`}>
                    {check.status.toUpperCase()}
                  </span>
                </div>
                {check.details?.checks && (
                  <div className="space-y-1.5 ml-8">
                    {check.details.checks.map((sub, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm">
                        <span className="mt-0.5 flex-shrink-0">
                          {sub.status === "passed" ? <CheckCircle2 className="w-3.5 h-3.5 text-green-500" /> :
                           sub.status === "failed" ? <XCircle className="w-3.5 h-3.5 text-red-500" /> :
                           <AlertTriangle className="w-3.5 h-3.5 text-yellow-500" />}
                        </span>
                        <span className="text-gray-700">{sub.message}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
    </ProtectedRoute>
  );
}
