"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, Shield, TrendingUp, Users, ArrowRight, CheckCircle2,
  Database, Loader2, LogIn, UserPlus, LogOut, LayoutDashboard,
  IndianRupee, Zap, Lock, BarChart3, Globe,
} from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const [seeding, setSeeding] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const { user, logout, isLoading } = useAuth();

  const getDashboardHref = () => {
    if (!user) return "/login";
    if (user.role === "vendor" && user.vendor_id) return `/vendor/${user.vendor_id}/dashboard`;
    if (user.role === "lender" && user.lender_id) return `/lender/${user.lender_id}/dashboard`;
    if (user.role === "admin") return "/admin/dashboard";
    return "/login";
  };

  const loadDemo = async () => {
    setSeeding(true);
    try {
      const r = await api.post("/seed/demo");
      if (r.data.seeded) {
        toast.success(`Demo loaded! ${r.data.created.vendors} vendors, ${r.data.created.invoices} invoices, ${r.data.created.lenders} lenders`);
        setSeeded(true);
      } else {
        toast.info("Demo data already exists");
        setSeeded(true);
      }
      await api.post("/seed/demo-users").catch(() => {});
    } catch {
      toast.error("Failed to seed demo data");
    }
    setSeeding(false);
  };

  return (
    <div className="min-h-screen font-[family-name:var(--font-geist-sans)]">
      {/* Header */}
      <header className="bg-white/90 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex justify-between items-center h-14">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
                <FileText className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-bold text-gray-900">
                Invo<span className="text-blue-600">X</span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={loadDemo} disabled={seeding || seeded}
                className="inline-flex items-center gap-1.5 bg-amber-500 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-amber-600 transition-colors disabled:opacity-60">
                {seeding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Database className="w-3.5 h-3.5" />}
                {seeded ? "Demo Loaded" : "Load Demo"}
              </button>
              {!isLoading && (
                <>
                  {user ? (
                    <>
                      <Link href={getDashboardHref()}
                        className="inline-flex items-center gap-1.5 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors">
                        <LayoutDashboard className="w-3.5 h-3.5" /> Dashboard
                      </Link>
                      <button onClick={logout}
                        className="inline-flex items-center gap-1.5 border border-gray-200 text-gray-600 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-gray-50 transition-colors">
                        <LogOut className="w-3.5 h-3.5" /> Logout
                      </button>
                    </>
                  ) : (
                    <>
                      <Link href="/login"
                        className="inline-flex items-center gap-1.5 border border-gray-200 text-gray-600 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-gray-50 transition-colors">
                        <LogIn className="w-3.5 h-3.5" /> Login
                      </Link>
                      <Link href="/register"
                        className="inline-flex items-center gap-1.5 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors">
                        <UserPlus className="w-3.5 h-3.5" /> Register
                      </Link>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800 text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 lg:py-16">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-1.5 bg-white/10 backdrop-blur-sm rounded-full px-3 py-1 text-xs mb-4">
              <Shield className="w-3.5 h-3.5" /> Blockchain-secured invoice financing
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight mb-4">
              Turn unpaid invoices into
              <span className="text-yellow-300"> instant capital</span>
            </h1>
            <p className="text-base text-blue-100 mb-6 leading-relaxed max-w-xl">
              InvoX helps MSMEs unlock 70–80% of invoice value instantly.
              No collateral. GST-verified. Blockchain-secured.
            </p>
            <div className="flex gap-3">
              {user ? (
                <Link href={getDashboardHref()}
                  className="inline-flex items-center gap-2 bg-white text-blue-700 px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-blue-50 transition-colors">
                  Go to Dashboard <ArrowRight className="w-4 h-4" />
                </Link>
              ) : (
                <Link href="/register"
                  className="inline-flex items-center gap-2 bg-white text-blue-700 px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-blue-50 transition-colors">
                  Get Started <ArrowRight className="w-4 h-4" />
                </Link>
              )}
              <Link href="/marketplace"
                className="inline-flex items-center gap-2 border border-white/30 text-white px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-white/10 transition-colors">
                <Globe className="w-4 h-4" /> Marketplace
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Stats strip */}
      <section className="bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            {[
              { icon: IndianRupee, label: "Total Funded", value: "₹8L+", color: "text-emerald-600" },
              { icon: Users, label: "Active Vendors", value: "3+", color: "text-blue-600" },
              { icon: BarChart3, label: "Avg Risk Score", value: "28", color: "text-violet-600" },
              { icon: Lock, label: "Blockchain Txns", value: "50+", color: "text-indigo-600" },
            ].map((s, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gray-50 rounded-xl flex items-center justify-center">
                  <s.icon className={`w-5 h-5 ${s.color}`} />
                </div>
                <div>
                  <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                  <p className="text-[11px] text-gray-400">{s.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works — 7-step flow */}
      <section className="py-10 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">How InvoX Works</h2>
          <p className="text-sm text-gray-500 text-center mb-8">Complete invoice financing in 7 simple steps</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              { step: "1", title: "Register", desc: "Sign up with KYC", color: "from-blue-500 to-blue-600" },
              { step: "2", title: "Auto-Verify", desc: "Govt API check", color: "from-indigo-500 to-indigo-600" },
              { step: "3", title: "Upload Bill", desc: "Create invoice", color: "from-violet-500 to-violet-600" },
              { step: "4", title: "List on Market", desc: "Lenders see it", color: "from-purple-500 to-purple-600" },
              { step: "5", title: "Get Funded", desc: "70-80% advance", color: "from-emerald-500 to-emerald-600" },
              { step: "6", title: "Repay", desc: "EMI installments", color: "from-amber-500 to-amber-600" },
              { step: "7", title: "Close", desc: "Invoice settled", color: "from-green-500 to-green-600" },
            ].map((s, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 p-3 text-center hover:shadow-md transition-shadow">
                <div className={`w-8 h-8 bg-gradient-to-br ${s.color} text-white rounded-lg flex items-center justify-center text-sm font-bold mx-auto mb-2`}>
                  {s.step}
                </div>
                <h3 className="text-xs font-bold text-gray-900">{s.title}</h3>
                <p className="text-[10px] text-gray-400 mt-0.5">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-10 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">Platform Features</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { icon: <Shield className="w-5 h-5" />, title: "GST-Verified Invoices", desc: "Every invoice verified against government GST records", color: "bg-blue-50 text-blue-600" },
              { icon: <TrendingUp className="w-5 h-5" />, title: "AI Risk Scoring", desc: "CIBIL, GST compliance & financials analyzed by AI", color: "bg-green-50 text-green-600" },
              { icon: <Users className="w-5 h-5" />, title: "Lender Marketplace", desc: "Multiple lenders compete to fund your invoices", color: "bg-purple-50 text-purple-600" },
              { icon: <Zap className="w-5 h-5" />, title: "Community Pot", desc: "Fractional tokenization for crowdfunded financing", color: "bg-amber-50 text-amber-600" },
              { icon: <Lock className="w-5 h-5" />, title: "Blockchain Proof", desc: "Immutable audit trail on custom blockchain", color: "bg-indigo-50 text-indigo-600" },
              { icon: <BarChart3 className="w-5 h-5" />, title: "AI Negotiation", desc: "Chat-based deal negotiation between parties", color: "bg-rose-50 text-rose-600" },
            ].map((f, i) => (
              <div key={i} className="flex items-start gap-3 p-4 rounded-xl border border-gray-100 hover:shadow-sm transition-shadow">
                <div className={`w-10 h-10 ${f.color} rounded-lg flex items-center justify-center flex-shrink-0`}>
                  {f.icon}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">{f.title}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Registration CTA */}
      <section className="py-8 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-6 sm:p-8 text-white text-center">
            <h2 className="text-xl sm:text-2xl font-bold mb-2">Ready to get funded?</h2>
            <p className="text-blue-100 text-sm mb-4 max-w-md mx-auto">
              Register with PAN, Aadhaar & GSTIN — your profile auto-verifies from government records.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link href="/register"
                className="inline-flex items-center justify-center gap-2 bg-white text-blue-700 px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-blue-50 transition-colors">
                <UserPlus className="w-4 h-4" /> Register as Vendor
              </Link>
              <Link href="/register"
                className="inline-flex items-center justify-center gap-2 border border-white/30 text-white px-6 py-2.5 rounded-xl text-sm font-semibold hover:bg-white/10 transition-colors">
                Start Lending
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* What you need */}
      <section className="py-8 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4 text-center">What you need to register</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {[
              "Personal PAN", "Aadhaar Card", "GSTIN", "CIBIL Score", "Bank Details",
              "Business Reg.", "Electricity Bill", "UDYAM (optional)", "Business PAN", "Nominee Details",
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                <span className="text-xs text-gray-600">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-6">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-md flex items-center justify-center">
              <FileText className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-sm font-bold text-white">Invo<span className="text-blue-400">X</span></span>
          </div>
          <p className="text-xs">&copy; 2026 InvoX. Embedded Invoice Financing for MSMEs.</p>
        </div>
      </footer>
    </div>
  );
}
