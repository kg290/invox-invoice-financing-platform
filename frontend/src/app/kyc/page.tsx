"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, Loader2, Shield, CheckCircle2, XCircle,
  AlertTriangle, User, CreditCard, MapPin, Building2,
  ArrowLeft, Fingerprint, BadgeCheck, Clock, Eye,
  Search, Database, ArrowRight, Globe, Phone, Mail,
  Banknote, BarChart3, FileCheck, ChevronRight,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface KYCCheck {
  check: string;
  status: "passed" | "failed" | "warning";
  message: string;
  source: string;
}

interface CitizenData {
  full_name: string;
  date_of_birth: string;
  gender: string;
  father_name: string;
  pan_number: string;
  aadhaar_number: string;
  aadhaar_full: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  phone: string;
  email: string;
  bank_account: string;
  bank_account_full: string;
  bank_ifsc: string;
  bank_name: string;
  bank_branch: string;
  annual_income: number;
  cibil_score: number;
  voter_id: string;
  passport_number: string;
  driving_license: string;
  gst_registered: boolean;
  gstin: string;
  employment_type: string;
}

type Step = "input" | "review" | "verified";

const statusConfig = {
  not_submitted: { bg: "bg-gray-50", border: "border-gray-200", text: "text-gray-600", icon: Clock, label: "Not Submitted" },
  pending: { bg: "bg-yellow-50", border: "border-yellow-200", text: "text-yellow-700", icon: Clock, label: "Pending Review" },
  in_review: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", icon: Eye, label: "Under Review" },
  verified: { bg: "bg-green-50", border: "border-green-200", text: "text-green-700", icon: CheckCircle2, label: "Verified" },
  rejected: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", icon: XCircle, label: "Rejected" },
};

export default function KYCPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [lookingUp, setLookingUp] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [kycStatus, setKycStatus] = useState<string>("not_submitted");
  const [checks, setChecks] = useState<KYCCheck[]>([]);
  const [submittedData, setSubmittedData] = useState<Record<string, unknown> | null>(null);
  const [citizen, setCitizen] = useState<CitizenData | null>(null);
  const [sources, setSources] = useState<string[]>([]);
  const [step, setStep] = useState<Step>("input");

  // Minimal input fields — just name + PAN
  const [name, setName] = useState("");
  const [pan, setPan] = useState("");

  const fetchStatus = async () => {
    try {
      const res = await api.get("/kyc/status");
      setKycStatus(res.data.kyc_status);
      setChecks(res.data.checks || []);
      setSubmittedData(res.data.submitted_data);
      if (res.data.kyc_status === "verified" || res.data.kyc_status === "rejected") {
        setStep("verified");
      }
    } catch { /* empty */ }
    setLoading(false);
  };

  useEffect(() => { fetchStatus(); }, []);

  // Step 1 → Step 2: Lookup citizen by name + PAN
  const handleLookup = async () => {
    if (!name.trim()) { toast.error("Please enter your full name"); return; }
    if (pan.length !== 10) { toast.error("PAN must be exactly 10 characters"); return; }

    setLookingUp(true);
    try {
      const res = await api.post("/kyc/lookup", {
        full_name: name.trim(),
        pan_number: pan.toUpperCase(),
      });
      setCitizen(res.data.citizen);
      setSources(res.data.sources || []);
      setStep("review");
      toast.success("Records found! Please review the extracted data.");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "No records found. Check your name and PAN."));
    }
    setLookingUp(false);
  };

  // Step 2 → Step 3: Verify extracted data
  const handleVerify = async () => {
    if (!citizen) return;
    setVerifying(true);
    try {
      const res = await api.post("/kyc/verify", {
        full_name: citizen.full_name,
        date_of_birth: citizen.date_of_birth,
        pan_number: citizen.pan_number,
        aadhaar_number: citizen.aadhaar_full,
        address: citizen.address,
        city: citizen.city,
        state: citizen.state,
        pincode: citizen.pincode,
        phone: citizen.phone,
        email: citizen.email,
        bank_account: citizen.bank_account_full,
        bank_ifsc: citizen.bank_ifsc,
        bank_name: citizen.bank_name,
        annual_income: citizen.annual_income,
        cibil_score: citizen.cibil_score,
        gstin: citizen.gstin,
        father_name: citizen.father_name,
        gender: citizen.gender,
      });
      setKycStatus(res.data.kyc_status);
      setChecks(res.data.checks || []);
      setStep("verified");
      toast.success(res.data.kyc_status === "verified" ? "KYC Verified Successfully!" : "Verification flagged issues");
      await fetchStatus();
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Verification failed"));
    }
    setVerifying(false);
  };

  const dashboardLink = user?.role === "vendor" && user.vendor_id
    ? `/vendor/${user.vendor_id}/dashboard`
    : user?.role === "lender" && user.lender_id
    ? `/lender/${user.lender_id}/dashboard`
    : "/";

  const sc = statusConfig[kycStatus as keyof typeof statusConfig] || statusConfig.not_submitted;
  const StatusIcon = sc.icon;

  const inputCls = "w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all bg-white";

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/20 to-indigo-50/30">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
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
            <Link href={dashboardLink} className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1">
              <ArrowLeft className="w-4 h-4" /> Dashboard
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Title */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Fingerprint className="w-7 h-7 text-blue-600" /> KYC Verification
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Smart identity verification — enter your name &amp; PAN, we auto-extract everything from government databases
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center gap-2 mb-8 bg-white rounded-xl border border-gray-200 p-4">
          {[
            { num: 1, label: "Enter Details", active: step === "input" },
            { num: 2, label: "Review Data", active: step === "review" },
            { num: 3, label: "Verification", active: step === "verified" },
          ].map((s, i) => (
            <div key={s.num} className="flex items-center gap-2 flex-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
                s.active ? "bg-blue-600 text-white" :
                (step === "review" && s.num === 1) || (step === "verified" && s.num <= 2) ? "bg-green-500 text-white" :
                "bg-gray-100 text-gray-400"
              }`}>
                {(step === "review" && s.num === 1) || (step === "verified" && s.num <= 2) ? "✓" : s.num}
              </div>
              <span className={`text-xs font-medium hidden sm:block ${s.active ? "text-blue-700" : "text-gray-400"}`}>{s.label}</span>
              {i < 2 && <ChevronRight className="w-4 h-4 text-gray-300 ml-auto" />}
            </div>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : (
          <>
            {/* ─── STEP 1: Minimal Input ─── */}
            {step === "input" && (
              <div className="space-y-6">
                {/* Status Banner if already submitted */}
                {kycStatus !== "not_submitted" && (
                  <div className={`rounded-xl border ${sc.border} ${sc.bg} p-5`}>
                    <div className="flex items-center gap-3">
                      <StatusIcon className={`w-6 h-6 ${sc.text}`} />
                      <div>
                        <p className={`font-semibold ${sc.text}`}>KYC Status: {sc.label}</p>
                        <p className="text-sm text-gray-600 mt-0.5">You can re-verify by entering your details below.</p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-5 text-white">
                    <h2 className="text-lg font-bold flex items-center gap-2">
                      <Search className="w-5 h-5" /> Identity Lookup
                    </h2>
                    <p className="text-blue-100 text-sm mt-1">
                      Just enter your full name and PAN number. Our system will automatically extract
                      all your details from government databases (UIDAI, NSDL, CIBIL, GST Network).
                    </p>
                  </div>

                  <div className="p-6 space-y-5">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">
                        Full Name <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          className={`${inputCls} pl-10`}
                          placeholder="e.g. Karnajeet Gosavi"
                        />
                      </div>
                      <p className="text-[11px] text-gray-400 mt-1">Enter your name as it appears on your PAN card</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1.5">
                        PAN Number <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <CreditCard className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          maxLength={10}
                          value={pan}
                          onChange={(e) => setPan(e.target.value.toUpperCase())}
                          className={`${inputCls} pl-10 tracking-widest font-mono`}
                          placeholder="ABCPD1234E"
                        />
                      </div>
                      <p className="text-[11px] text-gray-400 mt-1">10-character Permanent Account Number</p>
                    </div>

                    <button
                      onClick={handleLookup}
                      disabled={lookingUp}
                      className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl text-sm font-semibold
                        hover:shadow-lg hover:shadow-blue-200 disabled:opacity-60 inline-flex items-center justify-center gap-2
                        transition-all active:scale-[0.98]"
                    >
                      {lookingUp ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" /> Searching Government Databases...
                        </>
                      ) : (
                        <>
                          <Database className="w-4 h-4" /> Fetch My Details
                        </>
                      )}
                    </button>
                  </div>

                  {/* Info Box */}
                  <div className="mx-6 mb-6 bg-indigo-50 border border-indigo-200 rounded-xl p-4">
                    <div className="flex items-start gap-2">
                      <Shield className="w-4 h-4 text-indigo-500 mt-0.5 flex-shrink-0" />
                      <div className="text-xs text-indigo-700">
                        <p className="font-semibold mb-1">What happens when you click &quot;Fetch My Details&quot;?</p>
                        <ul className="space-y-0.5 text-indigo-600">
                          <li>• Your name &amp; PAN are searched across UIDAI, NSDL &amp; CIBIL databases</li>
                          <li>• All linked information (Aadhaar, Address, Bank, GST) is auto-extracted</li>
                          <li>• You review the extracted data before final verification</li>
                          <li>• No manual form filling required — everything is automatic</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ─── STEP 2: Review Extracted Data ─── */}
            {step === "review" && citizen && (
              <div className="space-y-6">
                {/* Success Banner */}
                <div className="rounded-xl border border-green-200 bg-green-50 p-5">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-6 h-6 text-green-600" />
                    <div>
                      <p className="font-semibold text-green-700">Records Found Successfully</p>
                      <p className="text-sm text-green-600 mt-0.5">
                        Data extracted from {sources.length} government sources. Review below and click Verify.
                      </p>
                    </div>
                  </div>
                  {/* Source badges */}
                  <div className="flex flex-wrap gap-2 mt-3">
                    {sources.map((s) => (
                      <span key={s} className="inline-flex items-center gap-1 px-2.5 py-1 bg-white border border-green-200 rounded-full text-[10px] font-medium text-green-700">
                        <Globe className="w-3 h-3" /> {s}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Personal Information */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
                    <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                      <User className="w-4 h-4 text-blue-600" /> Personal Information
                    </h3>
                  </div>
                  <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    <InfoField label="Full Name" value={citizen.full_name} icon={<User className="w-3.5 h-3.5" />} highlight />
                    <InfoField label="Date of Birth" value={citizen.date_of_birth} icon={<FileCheck className="w-3.5 h-3.5" />} />
                    <InfoField label="Gender" value={citizen.gender} />
                    <InfoField label="Father's Name" value={citizen.father_name} />
                    <InfoField label="Phone" value={citizen.phone} icon={<Phone className="w-3.5 h-3.5" />} />
                    <InfoField label="Email" value={citizen.email} icon={<Mail className="w-3.5 h-3.5" />} />
                  </div>
                </div>

                {/* Identity Documents */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
                    <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                      <CreditCard className="w-4 h-4 text-emerald-600" /> Identity Documents
                    </h3>
                  </div>
                  <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    <InfoField label="PAN Number" value={citizen.pan_number} icon={<CreditCard className="w-3.5 h-3.5" />} highlight />
                    <InfoField label="Aadhaar Number" value={citizen.aadhaar_number} icon={<Fingerprint className="w-3.5 h-3.5" />} highlight />
                    {citizen.voter_id && <InfoField label="Voter ID" value={citizen.voter_id} />}
                    {citizen.passport_number && <InfoField label="Passport" value={citizen.passport_number} />}
                    {citizen.driving_license && <InfoField label="Driving License" value={citizen.driving_license} />}
                  </div>
                </div>

                {/* Address */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
                    <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-orange-600" /> Address
                    </h3>
                  </div>
                  <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    <div className="sm:col-span-2 lg:col-span-3">
                      <InfoField label="Address" value={citizen.address} icon={<MapPin className="w-3.5 h-3.5" />} />
                    </div>
                    <InfoField label="City" value={citizen.city} />
                    <InfoField label="State" value={citizen.state} />
                    <InfoField label="Pincode" value={citizen.pincode} />
                  </div>
                </div>

                {/* Financial Information */}
                <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
                    <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                      <Banknote className="w-4 h-4 text-purple-600" /> Financial Information
                    </h3>
                  </div>
                  <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    <InfoField label="Bank Account" value={citizen.bank_account || "—"} icon={<Building2 className="w-3.5 h-3.5" />} />
                    <InfoField label="IFSC Code" value={citizen.bank_ifsc || "—"} />
                    <InfoField label="Bank Name" value={citizen.bank_name || "—"} />
                    <InfoField label="Bank Branch" value={citizen.bank_branch || "—"} />
                    <InfoField label="Annual Income" value={citizen.annual_income ? `₹${citizen.annual_income.toLocaleString("en-IN")}` : "—"} icon={<Banknote className="w-3.5 h-3.5" />} />
                    <InfoField label="CIBIL Score" value={citizen.cibil_score ? `${citizen.cibil_score}` : "—"} icon={<BarChart3 className="w-3.5 h-3.5" />}
                      badge={citizen.cibil_score >= 750 ? "Excellent" : citizen.cibil_score >= 650 ? "Good" : citizen.cibil_score > 0 ? "Fair" : undefined}
                      badgeColor={citizen.cibil_score >= 750 ? "green" : citizen.cibil_score >= 650 ? "blue" : "yellow"} />
                    {citizen.gst_registered && <InfoField label="GSTIN" value={citizen.gstin} highlight />}
                    <InfoField label="Employment" value={citizen.employment_type || "—"} />
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={() => { setStep("input"); setCitizen(null); }}
                    className="px-6 py-3.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                  >
                    ← Back
                  </button>
                  <button
                    onClick={handleVerify}
                    disabled={verifying}
                    className="flex-1 py-3.5 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl text-sm font-semibold
                      hover:shadow-lg hover:shadow-green-200 disabled:opacity-60 inline-flex items-center justify-center gap-2
                      transition-all active:scale-[0.98]"
                  >
                    {verifying ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" /> Running Verification...
                      </>
                    ) : (
                      <>
                        <BadgeCheck className="w-5 h-5" /> Verify Identity
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* ─── STEP 3: Verification Results ─── */}
            {step === "verified" && (
              <div className="space-y-6">
                {/* Status Banner */}
                <div className={`rounded-xl border ${sc.border} ${sc.bg} p-5`}>
                  <div className="flex items-center gap-3">
                    <StatusIcon className={`w-6 h-6 ${sc.text}`} />
                    <div>
                      <p className={`font-semibold text-lg ${sc.text}`}>KYC Status: {sc.label}</p>
                      <p className="text-sm text-gray-600 mt-0.5">
                        {kycStatus === "verified" && "Your identity has been fully verified. All platform features are now unlocked."}
                        {kycStatus === "rejected" && "Verification failed. Please re-submit with correct details."}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Submitted Data Summary */}
                {submittedData && (
                  <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
                      <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                        <User className="w-4 h-4 text-blue-600" /> Verified Profile
                      </h3>
                    </div>
                    <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                      <InfoField label="Full Name" value={submittedData.full_name as string} highlight />
                      <InfoField label="Date of Birth" value={submittedData.date_of_birth as string} />
                      <InfoField label="Gender" value={submittedData.gender as string} />
                      <InfoField label="PAN Number" value={submittedData.pan_number as string} />
                      <InfoField label="Aadhaar" value={submittedData.aadhaar_number as string} />
                      <InfoField label="Address" value={`${submittedData.city}, ${submittedData.state} - ${submittedData.pincode}`} />
                      {Boolean(submittedData.bank_name) && <InfoField label="Bank" value={`${submittedData.bank_name} (${submittedData.bank_account})`} />}
                      {Number(submittedData.cibil_score) > 0 && <InfoField label="CIBIL Score" value={String(submittedData.cibil_score)} />}
                      {Boolean(submittedData.gstin) && <InfoField label="GSTIN" value={submittedData.gstin as string} />}
                    </div>
                  </div>
                )}

                {/* Verification Checks */}
                {checks.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                      <Shield className="w-4 h-4 text-blue-600" /> Verification Results ({checks.filter(c => c.status === "passed").length}/{checks.length} Passed)
                    </h3>
                    <div className="grid gap-2">
                      {checks.map((check, idx) => (
                        <div key={idx} className={`rounded-xl border p-4 ${
                          check.status === "passed" ? "bg-green-50/70 border-green-200" :
                          check.status === "failed" ? "bg-red-50/70 border-red-200" :
                          "bg-yellow-50/70 border-yellow-200"
                        }`}>
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              {check.status === "passed" && <CheckCircle2 className="w-4 h-4 text-green-500" />}
                              {check.status === "failed" && <XCircle className="w-4 h-4 text-red-500" />}
                              {check.status === "warning" && <AlertTriangle className="w-4 h-4 text-yellow-500" />}
                              <span className="text-sm font-semibold text-gray-900">{check.check}</span>
                            </div>
                            <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                              check.status === "passed" ? "bg-green-100 text-green-700" :
                              check.status === "failed" ? "bg-red-100 text-red-700" :
                              "bg-yellow-100 text-yellow-700"
                            }`}>
                              {check.status.toUpperCase()}
                            </span>
                          </div>
                          <p className="text-xs text-gray-700 ml-6">{check.message}</p>
                          <p className="text-[10px] text-gray-400 ml-6 mt-0.5">Source: {check.source}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  {kycStatus !== "verified" && (
                    <button
                      onClick={() => { setStep("input"); setCitizen(null); setChecks([]); }}
                      className="flex-1 py-3.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition-colors inline-flex items-center justify-center gap-2"
                    >
                      <ArrowRight className="w-4 h-4" /> Try Again
                    </button>
                  )}
                  <Link href={dashboardLink}
                    className="flex-1 py-3.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors text-center"
                  >
                    Back to Dashboard
                  </Link>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
    </ProtectedRoute>
  );
}


/* ─── Reusable Info Field Component ─── */
function InfoField({ label, value, icon, highlight, badge, badgeColor }: {
  label: string; value: string; icon?: React.ReactNode; highlight?: boolean;
  badge?: string; badgeColor?: string;
}) {
  if (!value || value === "—") {
    return (
      <div>
        <span className="text-[11px] text-gray-400 block mb-0.5">{label}</span>
        <p className="text-sm text-gray-300">—</p>
      </div>
    );
  }
  return (
    <div>
      <span className="text-[11px] text-gray-400 block mb-0.5">{label}</span>
      <p className={`text-sm font-medium flex items-center gap-1.5 ${highlight ? "text-blue-700" : "text-gray-900"}`}>
        {icon && <span className="text-gray-400">{icon}</span>}
        {value}
        {badge && (
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ml-1 ${
            badgeColor === "green" ? "bg-green-100 text-green-700" :
            badgeColor === "blue" ? "bg-blue-100 text-blue-700" :
            "bg-yellow-100 text-yellow-700"
          }`}>{badge}</span>
        )}
      </p>
    </div>
  );
}
