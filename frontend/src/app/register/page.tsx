"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, Mail, Lock, Loader2, Eye, EyeOff, User, Phone,
  Smartphone, MessageCircle, Building2, Briefcase, CreditCard, Fingerprint, Hash,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "", email: "", phone: "", password: "", confirmPassword: "",
    role: "vendor", otp_channel: "email",
    organization: "", lender_type: "individual",
    pan_number: "", aadhaar_number: "", gstin: "",
  });
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.email || !form.phone || !form.password) {
      toast.error("All fields are required"); return;
    }
    if (form.password !== form.confirmPassword) {
      toast.error("Passwords do not match"); return;
    }
    if (form.password.length < 6) {
      toast.error("Password must be at least 6 characters"); return;
    }
    if (form.role === "vendor") {
      if (!form.pan_number || !form.aadhaar_number || !form.gstin) {
        toast.error("PAN, Aadhaar and GSTIN are required for vendor registration"); return;
      }
    }
    setLoading(true);
    try {
      const payload: Record<string, string> = {
        name: form.name, email: form.email, phone: form.phone,
        password: form.password, role: form.role, otp_channel: form.otp_channel,
      };
      if (form.role === "lender") {
        payload.organization = form.organization;
        payload.lender_type = form.lender_type;
      }
      if (form.role === "vendor") {
        payload.pan_number = form.pan_number;
        payload.aadhaar_number = form.aadhaar_number;
        payload.gstin = form.gstin;
      }
      const r = await api.post("/auth/register", payload);
      toast.success(`Account created! OTP sent via ${form.otp_channel}`);
      if (r.data.debug_otp) {
        toast.info(`Demo OTP: ${r.data.debug_otp}`, { duration: 15000 });
      }
      router.push(`/verify-otp?email=${encodeURIComponent(form.email)}`);
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Registration failed"));
    }
    setLoading(false);
  };

  const channels = [
    { value: "email", label: "Email", icon: Mail },
    { value: "sms", label: "SMS", icon: Smartphone },
    { value: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  ];

  const inputCls = "w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 outline-none bg-white";

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-6">
          <Link href="/" className="inline-flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-bold text-gray-900">Invo<span className="text-blue-600">X</span></span>
          </Link>
          <p className="text-gray-500 text-sm mt-2">Create your InvoX account</p>
        </div>

        <div className="bg-white rounded-2xl border shadow-sm p-8">
          {/* Role selector */}
          <div className="flex gap-3 mb-6">
            <button type="button" onClick={() => setForm({ ...form, role: "vendor" })}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium border-2 transition-all ${
                form.role === "vendor"
                  ? "bg-blue-50 border-blue-500 text-blue-700"
                  : "bg-white border-gray-200 text-gray-500 hover:bg-gray-50"
              }`}>
              <Briefcase className="w-4 h-4" /> Vendor (MSME)
            </button>
            <button type="button" onClick={() => setForm({ ...form, role: "lender" })}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium border-2 transition-all ${
                form.role === "lender"
                  ? "bg-green-50 border-green-500 text-green-700"
                  : "bg-white border-gray-200 text-gray-500 hover:bg-gray-50"
              }`}>
              <Building2 className="w-4 h-4" /> Lender
            </button>
          </div>

          <form onSubmit={handleRegister} className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Full Name *</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className={`${inputCls} pl-10`} placeholder="Your name" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Phone *</label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    className={`${inputCls} pl-10`} placeholder="9876543210" />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Email Address *</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className={`${inputCls} pl-10`} placeholder="you@example.com" />
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Password *</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input type={showPw ? "text" : "password"} value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    className={`${inputCls} pl-10 pr-10`} placeholder="Min 6 chars" />
                  <button type="button" onClick={() => setShowPw(!showPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Confirm Password *</label>
                <input type="password" value={form.confirmPassword}
                  onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                  className={inputCls} placeholder="Repeat password" />
              </div>
            </div>

            {/* Lender-specific fields */}
            {form.role === "lender" && (
              <div className="grid sm:grid-cols-2 gap-4 p-4 bg-green-50 rounded-xl">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Organization</label>
                  <input value={form.organization} onChange={(e) => setForm({ ...form, organization: e.target.value })}
                    className={inputCls} placeholder="Company / NBFC name" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                  <select value={form.lender_type} onChange={(e) => setForm({ ...form, lender_type: e.target.value })}
                    className={`${inputCls} bg-white`}>
                    <option value="individual">Individual</option>
                    <option value="nbfc">NBFC</option>
                    <option value="bank">Bank</option>
                  </select>
                </div>
              </div>
            )}

            {/* Vendor auto-KYC fields */}
            {form.role === "vendor" && (
              <div className="space-y-3 p-4 bg-blue-50 rounded-xl">
                <div className="flex items-center gap-2 mb-1">
                  <Fingerprint className="w-4 h-4 text-blue-600" />
                  <span className="text-xs font-semibold text-blue-700">Identity & Business Verification</span>
                  <span className="text-[10px] bg-blue-100 text-blue-600 px-2 py-0.5 rounded-full font-medium">Auto-verified</span>
                </div>
                <p className="text-[11px] text-blue-500 -mt-1 mb-2">Your profile will be auto-filled from government records after OTP verification</p>
                <div className="grid sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">PAN Number *</label>
                    <div className="relative">
                      <CreditCard className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input value={form.pan_number} onChange={(e) => setForm({ ...form, pan_number: e.target.value.toUpperCase() })}
                        className={`${inputCls} pl-10`} placeholder="ABCDE1234F" maxLength={10} />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Aadhaar Number *</label>
                    <div className="relative">
                      <Fingerprint className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input value={form.aadhaar_number} onChange={(e) => setForm({ ...form, aadhaar_number: e.target.value.replace(/\D/g, '').slice(0, 12) })}
                        className={`${inputCls} pl-10`} placeholder="123412341234" maxLength={12} />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">GSTIN *</label>
                    <div className="relative">
                      <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input value={form.gstin} onChange={(e) => setForm({ ...form, gstin: e.target.value.toUpperCase() })}
                        className={`${inputCls} pl-10`} placeholder="22ABCDE1234F1Z5" maxLength={15} />
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-2">OTP Delivery Channel</label>
              <div className="flex gap-2">
                {channels.map((ch) => (
                  <button key={ch.value} type="button"
                    onClick={() => setForm({ ...form, otp_channel: ch.value })}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-medium border transition-colors ${
                      form.otp_channel === ch.value
                        ? "bg-blue-50 border-blue-300 text-blue-700"
                        : "bg-white border-gray-200 text-gray-500 hover:bg-gray-50"
                    }`}>
                    <ch.icon className="w-3.5 h-3.5" /> {ch.label}
                  </button>
                ))}
              </div>
            </div>

            <button type="submit" disabled={loading}
              className={`w-full py-3 text-white rounded-xl text-sm font-semibold disabled:opacity-60 flex items-center justify-center gap-2 transition-all ${
                form.role === "vendor"
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                  : "bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
              }`}>
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {loading ? "Creating Account..." : `Register as ${form.role === "vendor" ? "Vendor" : "Lender"}`}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            Already have an account?{" "}
            <Link href="/login" className="text-blue-600 font-medium hover:text-blue-700">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
