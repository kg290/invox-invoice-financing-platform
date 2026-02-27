"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";
import {
  FileText,
  User,
  CreditCard,
  Fingerprint,
  Building2,
  ArrowRight,
  Loader2,
  AlertCircle,
  BadgeCheck,
  XCircle,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { vendorQuickSchema, VendorQuickSchemaType } from "@/lib/validation";

interface VerificationCheck {
  check: string;
  status: "passed" | "failed" | "warning";
  message: string;
}

interface QuickRegisterResponse {
  id: number;
  full_name: string;
  business_name: string;
  profile_status: string;
  risk_score: number | null;
  cibil_score: number | null;
  gstin: string;
  personal_pan: string;
  city: string;
  state: string;
  business_type: string;
  business_category: string;
  verification_checks?: VerificationCheck[];
}

export default function VendorRegister() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<QuickRegisterResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const { updateUser } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<VendorQuickSchemaType>({
    resolver: zodResolver(vendorQuickSchema),
    mode: "onBlur",
  });

  const onSubmit = async (data: VendorQuickSchemaType) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const payload = {
        full_name: data.full_name.trim(),
        personal_pan: data.personal_pan.trim().toUpperCase(),
        personal_aadhaar: data.personal_aadhaar.trim(),
        gstin: data.gstin.trim().toUpperCase(),
      };
      const res = await api.post("/vendors/quick-register", payload);
      const vendor: QuickRegisterResponse = res.data;
      setResult(vendor);
      updateUser({ vendor_id: vendor.id });
      toast.success("Vendor profile created & verified!");
    } catch (err: unknown) {
      const e = err as {
        response?: { data?: { detail?: string } };
      };
      const msg =
        e?.response?.data?.detail ||
        getErrorMessage(err, "Registration failed. Please try again.");
      setError(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClass =
    "w-full px-4 py-3 border border-gray-300 rounded-xl text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all placeholder:text-gray-400 bg-white";
  const labelClass = "block text-sm font-semibold text-gray-700 mb-1.5";
  const errorMsgClass = "text-red-500 text-xs mt-1 flex items-center gap-1";

  // -- Success view after registration --
  if (result) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center p-4 font-[family-name:var(--font-geist-sans)]">
          <div className="w-full max-w-lg">
            <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
              {/* Success header */}
              <div className="bg-gradient-to-r from-green-500 to-emerald-600 px-8 py-8 text-center">
                <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 className="w-10 h-10 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-white">Registration Successful!</h1>
                <p className="text-green-100 text-sm mt-2">
                  Your vendor profile has been created and verified automatically.
                </p>
              </div>

              {/* Vendor summary */}
              <div className="p-8 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <SummaryItem label="Name" value={result.full_name} />
                  <SummaryItem label="Business" value={result.business_name} />
                  <SummaryItem label="GSTIN" value={result.gstin} />
                  <SummaryItem label="PAN" value={result.personal_pan} />
                  <SummaryItem label="Type" value={result.business_type} />
                  <SummaryItem label="Category" value={result.business_category} />
                  <SummaryItem label="Location" value={`${result.city}, ${result.state}`} />
                  <SummaryItem
                    label="Status"
                    value={result.profile_status === "verified" ? "Verified" : "Pending Review"}
                    highlight={result.profile_status === "verified"}
                  />
                  {result.cibil_score && (
                    <SummaryItem label="CIBIL Score" value={String(result.cibil_score)} />
                  )}
                  {result.risk_score != null && (
                    <SummaryItem label="Risk Score" value={`${result.risk_score}/100`} />
                  )}
                </div>

                {/* Verification checks */}
                {result.verification_checks && result.verification_checks.length > 0 && (
                  <div className="mt-6 border-t pt-4">
                    <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-blue-600" />
                      Government Verification
                    </h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {result.verification_checks.map((c, i) => (
                        <div
                          key={i}
                          className={`flex items-center gap-3 text-sm px-3 py-2 rounded-lg ${
                            c.status === "passed"
                              ? "bg-green-50 text-green-700"
                              : c.status === "failed"
                              ? "bg-red-50 text-red-700"
                              : "bg-amber-50 text-amber-700"
                          }`}
                        >
                          {c.status === "passed" ? (
                            <BadgeCheck className="w-4 h-4 flex-shrink-0" />
                          ) : c.status === "failed" ? (
                            <XCircle className="w-4 h-4 flex-shrink-0" />
                          ) : (
                            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
                          )}
                          <span className="font-medium">{c.check}:</span>
                          <span className="truncate">{c.message}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  onClick={() => router.push(`/vendor/${result.id}/dashboard`)}
                  className="w-full mt-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-200"
                >
                  Go to Dashboard
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  // -- Registration form --
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center p-4 font-[family-name:var(--font-geist-sans)]">
        <div className="w-full max-w-lg">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 justify-center mb-8">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold text-gray-900">
              Invo<span className="text-blue-600">X</span>
            </span>
          </Link>

          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-700 px-8 py-7 text-center">
              <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-3">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-white">Smart Registration</h1>
              <p className="text-blue-100 text-sm mt-2">
                Enter just 4 details — we auto-fetch everything from Government databases
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit(onSubmit)} className="p-8 space-y-5">
              {/* Full Name */}
              <div>
                <label htmlFor="full_name" className={labelClass}>
                  <span className="flex items-center gap-2">
                    <User className="w-4 h-4 text-gray-400" />
                    Full Name (as on PAN)
                  </span>
                </label>
                <input
                  id="full_name"
                  type="text"
                  placeholder="e.g. Karnajeet Gosavi"
                  className={inputClass}
                  {...register("full_name")}
                />
                {errors.full_name && (
                  <p className={errorMsgClass}>
                    <AlertCircle className="w-3 h-3" />
                    {errors.full_name.message}
                  </p>
                )}
              </div>

              {/* PAN */}
              <div>
                <label htmlFor="personal_pan" className={labelClass}>
                  <span className="flex items-center gap-2">
                    <CreditCard className="w-4 h-4 text-gray-400" />
                    PAN Number
                  </span>
                </label>
                <input
                  id="personal_pan"
                  type="text"
                  placeholder="e.g. GOPKG1234A"
                  className={`${inputClass} uppercase`}
                  maxLength={10}
                  {...register("personal_pan", {
                    onChange: (e) => {
                      e.target.value = e.target.value.toUpperCase();
                    },
                  })}
                />
                {errors.personal_pan && (
                  <p className={errorMsgClass}>
                    <AlertCircle className="w-3 h-3" />
                    {errors.personal_pan.message}
                  </p>
                )}
              </div>

              {/* Aadhaar */}
              <div>
                <label htmlFor="personal_aadhaar" className={labelClass}>
                  <span className="flex items-center gap-2">
                    <Fingerprint className="w-4 h-4 text-gray-400" />
                    Aadhaar Number
                  </span>
                </label>
                <input
                  id="personal_aadhaar"
                  type="text"
                  placeholder="e.g. 987654321012"
                  className={inputClass}
                  maxLength={12}
                  {...register("personal_aadhaar")}
                />
                {errors.personal_aadhaar && (
                  <p className={errorMsgClass}>
                    <AlertCircle className="w-3 h-3" />
                    {errors.personal_aadhaar.message}
                  </p>
                )}
              </div>

              {/* GSTIN */}
              <div>
                <label htmlFor="gstin" className={labelClass}>
                  <span className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-gray-400" />
                    GSTIN
                  </span>
                </label>
                <input
                  id="gstin"
                  type="text"
                  placeholder="e.g. 27GOPKG1234A1ZP"
                  className={`${inputClass} uppercase`}
                  maxLength={15}
                  {...register("gstin", {
                    onChange: (e) => {
                      e.target.value = e.target.value.toUpperCase();
                    },
                  })}
                />
                {errors.gstin && (
                  <p className={errorMsgClass}>
                    <AlertCircle className="w-3 h-3" />
                    {errors.gstin.message}
                  </p>
                )}
              </div>

              {/* Auto-fetch info */}
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-700">
                <p className="font-semibold flex items-center gap-2 mb-1">
                  <Sparkles className="w-4 h-4" />
                  Smart Fill Technology
                </p>
                <p className="text-blue-600 text-xs leading-relaxed">
                  Personal details, business info, bank accounts, GST compliance,
                  CIBIL score, and nominee data are automatically fetched from
                  government databases — no manual entry needed.
                </p>
              </div>

              {/* Error display */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  <div>{error}</div>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-200 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Verifying & Registering...
                  </>
                ) : (
                  <>
                    Register & Verify
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>

              <p className="text-center text-xs text-gray-400 mt-4">
                By registering, you authorize InvoX to verify your identity
                with government databases.
              </p>
            </form>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

/* -- Helper: summary display item -- */
function SummaryItem({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p
        className={`text-sm font-medium ${
          highlight ? "text-green-600" : "text-gray-900"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
