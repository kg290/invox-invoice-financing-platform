"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { FileText, ShieldCheck, Loader2, RefreshCw } from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function OTPContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const email = searchParams.get("email") || "";

  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(300); // 5 min
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    inputRefs.current[0]?.focus();
    const t = setInterval(() => setCountdown((c) => (c > 0 ? c - 1 : 0)), 1000);
    return () => clearInterval(t);
  }, []);

  const handleChange = (idx: number, val: string) => {
    if (val.length > 1) val = val[val.length - 1];
    if (!/^\d*$/.test(val)) return;
    const newOtp = [...otp];
    newOtp[idx] = val;
    setOtp(newOtp);
    if (val && idx < 5) inputRefs.current[idx + 1]?.focus();
  };

  const handleKeyDown = (idx: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[idx] && idx > 0) {
      inputRefs.current[idx - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (text.length === 6) {
      setOtp(text.split(""));
      inputRefs.current[5]?.focus();
    }
  };

  const verifyOtp = async () => {
    const code = otp.join("");
    if (code.length !== 6) { toast.error("Enter 6-digit OTP"); return; }
    setLoading(true);
    try {
      const r = await api.post("/auth/verify-otp", { email, otp: code });
      login(r.data);
      toast.success("Verified successfully!");
      // Redirect based on role
      const user = r.data.user;
      if (user.role === "vendor") {
        if (user.vendor_id) {
          router.push(`/vendor/${user.vendor_id}/dashboard`);
        } else {
          router.push("/vendor/register");
        }
      } else if (user.role === "lender") {
        if (user.lender_id) {
          router.push(`/lender/${user.lender_id}/dashboard`);
        } else {
          router.push("/marketplace");
        }
      } else {
        router.push("/");
      }
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Invalid OTP"));
      setOtp(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    }
    setLoading(false);
  };

  const resendOtp = async () => {
    setResending(true);
    try {
      // Need password — for demo, use a dummy resend that generates new OTP
      const r = await api.post("/auth/login", { email, password: "resend-dummy", otp_channel: "email" });
      toast.success("OTP resent!");
      if (r.data.debug_otp) {
        toast.info(`Demo OTP: ${r.data.debug_otp}`, { duration: 15000 });
      }
      setCountdown(300);
    } catch {
      toast.info("Please login again to get a new OTP");
      router.push("/login");
    }
    setResending(false);
  };

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-bold text-gray-900">Invo<span className="text-blue-600">X</span></span>
          </Link>
        </div>

        <div className="bg-white rounded-2xl border shadow-sm p-8 text-center">
          <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <ShieldCheck className="w-8 h-8 text-blue-600" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 mb-1">Verify OTP</h1>
          <p className="text-sm text-gray-500 mb-6">
            Enter the 6-digit code sent to<br />
            <span className="font-medium text-gray-700">{email}</span>
          </p>

          {/* OTP Input Grid */}
          <div className="flex justify-center gap-3 mb-6" onPaste={handlePaste}>
            {otp.map((digit, idx) => (
              <input
                key={idx}
                ref={(el) => { inputRefs.current[idx] = el; }}
                type="text"
                inputMode="numeric"
                value={digit}
                onChange={(e) => handleChange(idx, e.target.value)}
                onKeyDown={(e) => handleKeyDown(idx, e)}
                className="w-12 h-14 text-center text-xl font-bold text-gray-900 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all"
                maxLength={1}
              />
            ))}
          </div>

          {/* Timer */}
          <p className={`text-sm mb-4 ${countdown > 0 ? "text-gray-500" : "text-red-500"}`}>
            {countdown > 0 ? `Expires in ${formatTime(countdown)}` : "OTP expired"}
          </p>

          <button onClick={verifyOtp} disabled={loading || otp.join("").length !== 6}
            className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-indigo-700 disabled:opacity-60 flex items-center justify-center gap-2">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
            {loading ? "Verifying..." : "Verify & Continue"}
          </button>

          <button onClick={resendOtp} disabled={resending}
            className="mt-4 text-sm text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-1 disabled:opacity-60">
            {resending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Resend OTP
          </button>
        </div>

        <p className="text-center text-xs text-gray-400 mt-4">
          OTP is valid for 5 minutes. Check your inbox, SMS, or WhatsApp.
        </p>
      </div>
    </div>
  );
}

export default function VerifyOTPPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    }>
      <OTPContent />
    </Suspense>
  );
}
