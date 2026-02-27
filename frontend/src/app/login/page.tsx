"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { FileText, Mail, Lock, Loader2, Eye, EyeOff, Smartphone, MessageCircle, Zap, UserCircle, Landmark } from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const DEMO_ACCOUNTS = [
  { role: "Vendor 1", email: "vendor1@invox.demo", password: "Demo@1234", icon: UserCircle, desc: "Sunita — Maa Annapurna Tiffin", activeBg: "bg-amber-50 border-amber-300", iconColor: "text-amber-600", badgeCls: "bg-amber-100 text-amber-700" },
  { role: "Vendor 2", email: "vendor2@invox.demo", password: "Demo@1234", icon: UserCircle, desc: "Ramu — Furniture Works", activeBg: "bg-blue-50 border-blue-300", iconColor: "text-blue-600", badgeCls: "bg-blue-100 text-blue-700" },
  { role: "Vendor 3", email: "vendor3@invox.demo", password: "Demo@1234", icon: UserCircle, desc: "Fatima — Khan Masala & Spices", activeBg: "bg-emerald-50 border-emerald-300", iconColor: "text-emerald-600", badgeCls: "bg-emerald-100 text-emerald-700" },
  { role: "Lender", email: "lender@invox.demo", password: "Demo@1234", icon: Landmark, desc: "Deepak — JanSeva Microfinance", activeBg: "bg-purple-50 border-purple-300", iconColor: "text-purple-600", badgeCls: "bg-purple-100 text-purple-700" },
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "", otp_channel: "email" });
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.email || !form.password) { toast.error("Email and password required"); return; }
    setLoading(true);
    try {
      const r = await api.post("/auth/login", form);

      // Demo accounts auto-verify — skip OTP page
      if (r.data.auto_verified) {
        login({
          access_token: r.data.access_token,
          refresh_token: r.data.refresh_token,
          token_type: r.data.token_type,
          user: r.data.user,
        });
        toast.success("Welcome back!");
        const u = r.data.user;
        if (u.role === "vendor" && u.vendor_id) {
          router.push(`/vendor/${u.vendor_id}/dashboard`);
        } else if (u.role === "lender" && u.lender_id) {
          router.push(`/lender/${u.lender_id}/dashboard`);
        } else {
          router.push("/");
        }
        return;
      }

      toast.success(`OTP sent via ${form.otp_channel}!`);
      if (r.data.debug_otp) {
        toast.info(`Demo OTP: ${r.data.debug_otp}`, { duration: 15000 });
      }
      router.push(`/verify-otp?email=${encodeURIComponent(form.email)}`);
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Login failed"));
    }
    setLoading(false);
  };

  const fillDemo = (account: typeof DEMO_ACCOUNTS[0]) => {
    setForm({ email: account.email, password: account.password, otp_channel: "email" });
  };

  const channels = [
    { value: "email", label: "Email", icon: Mail },
    { value: "sms", label: "SMS", icon: Smartphone },
    { value: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  ];

  const inputCls = "w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 outline-none bg-white";

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-bold text-gray-900">Invo<span className="text-blue-600">X</span></span>
          </Link>
          <p className="text-gray-500 text-sm mt-2">Sign in to your account</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border shadow-sm p-8">
          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className={`${inputCls} pl-10`} placeholder="you@example.com" />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input type={showPw ? "text" : "password"} value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className={`${inputCls} pl-10 pr-10`} placeholder="••••••••" />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

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
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-indigo-700 disabled:opacity-60 flex items-center justify-center gap-2 transition-all">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {loading ? "Sending OTP..." : "Sign In"}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-blue-600 font-medium hover:text-blue-700">Create account</Link>
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-4">
          Secured with 2-Factor OTP Authentication
        </p>

        {/* Demo Quick Login */}
        <div className="mt-6 bg-white rounded-2xl border shadow-sm p-5">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-amber-500" />
            <span className="text-sm font-semibold text-gray-900">Quick Demo Login</span>
            <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">No OTP needed</span>
          </div>
          <div className="space-y-2">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.email}
                type="button"
                onClick={() => fillDemo(acc)}
                className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left hover:shadow-sm ${
                  form.email === acc.email
                    ? acc.activeBg
                    : "bg-gray-50 border-gray-200 hover:bg-gray-100"
                }`}
              >
                <acc.icon className={`w-8 h-8 ${acc.iconColor} flex-shrink-0`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-900">{acc.desc}</div>
                  <div className="text-xs text-gray-500 truncate">{acc.email}</div>
                </div>
                <span className={`text-[10px] font-semibold px-2 py-1 rounded-lg ${acc.badgeCls}`}>
                  {acc.role}
                </span>
              </button>
            ))}
          </div>
          <p className="text-[11px] text-gray-400 mt-3 text-center">
            Click any account above, then press <strong>Sign In</strong> — no OTP step.
          </p>
        </div>
      </div>
    </div>
  );
}
