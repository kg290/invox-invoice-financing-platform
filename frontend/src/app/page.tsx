"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText,
  Shield,
  TrendingUp,
  Users,
  ArrowRight,
  CheckCircle2,
  Database,
  Loader2,
  LogIn,
  UserPlus,
  LogOut,
  LayoutDashboard,
} from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const [seeding, setSeeding] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const { user, logout } = useAuth();

  const getDashboardHref = () => {
    if (!user) return "/login";
    if (user.role === "vendor" && user.vendor_id) return `/vendor/${user.vendor_id}/dashboard`;
    if (user.role === "lender" && user.lender_id) return `/lender/${user.lender_id}/dashboard`;
    return "/vendor/register";
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
    } catch {
      toast.error("Failed to seed demo data");
    }
    setSeeding(false);
  };

  return (
    <div className="min-h-screen font-[family-name:var(--font-geist-sans)]">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">
                Invo<span className="text-blue-600">X</span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={loadDemo}
                disabled={seeding || seeded}
                className="inline-flex items-center gap-1.5 bg-amber-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-60"
              >
                {seeding ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
                {seeded ? "Demo Loaded" : "Load Demo Data"}
              </button>
              {user ? (
                <>
                  <Link
                    href={getDashboardHref()}
                    className="inline-flex items-center gap-1.5 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    Dashboard
                  </Link>
                  <button
                    onClick={logout}
                    className="inline-flex items-center gap-1.5 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="inline-flex items-center gap-1.5 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
                  >
                    <LogIn className="w-4 h-4" />
                    Login
                  </Link>
                  <Link
                    href="/register"
                    className="inline-flex items-center gap-1.5 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                  >
                    <UserPlus className="w-4 h-4" />
                    Register
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-1.5 text-sm mb-6">
              <Shield className="w-4 h-4" />
              Blockchain-secured invoice financing
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6">
              Turn unpaid invoices into
              <span className="text-yellow-300"> instant working capital</span>
            </h1>
            <p className="text-lg sm:text-xl text-blue-100 mb-8 leading-relaxed">
              InvoX helps MSMEs unlock 70–80% of their invoice value instantly.
              No collateral needed. GST-verified. Blockchain-secured.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              {user ? (
                <Link
                  href={getDashboardHref()}
                  className="inline-flex items-center justify-center gap-2 bg-white text-blue-700 px-8 py-3.5 rounded-xl text-lg font-semibold hover:bg-blue-50 transition-colors"
                >
                  Go to Dashboard <ArrowRight className="w-5 h-5" />
                </Link>
              ) : (
                <Link
                  href="/register"
                  className="inline-flex items-center justify-center gap-2 bg-white text-blue-700 px-8 py-3.5 rounded-xl text-lg font-semibold hover:bg-blue-50 transition-colors"
                >
                  Get Started <ArrowRight className="w-5 h-5" />
                </Link>
              )}
              <Link
                href="/login"
                className="inline-flex items-center justify-center gap-2 border-2 border-white/30 text-white px-8 py-3.5 rounded-xl text-lg font-semibold hover:bg-white/10 transition-colors"
              >
                <LogIn className="w-5 h-5" /> Login
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Why MSMEs choose InvoX
            </h2>
            <p className="text-gray-600 text-lg max-w-2xl mx-auto">
              A complete invoice financing ecosystem built for India&apos;s small businesses
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: <Shield className="w-7 h-7" />,
                title: "GST-Verified Invoices",
                desc: "Every invoice is verified against GST records to ensure authenticity before financing.",
                color: "bg-blue-50 text-blue-600",
              },
              {
                icon: <TrendingUp className="w-7 h-7" />,
                title: "AI Risk Scoring",
                desc: "Advanced AI analyzes vendor history, payment patterns and financials for accurate risk assessment.",
                color: "bg-green-50 text-green-600",
              },
              {
                icon: <Users className="w-7 h-7" />,
                title: "Lender Marketplace",
                desc: "Connect with multiple lenders competing to fund your invoices at the best rates.",
                color: "bg-purple-50 text-purple-600",
              },
            ].map((f, i) => (
              <div
                key={i}
                className="p-8 rounded-2xl border border-gray-100 hover:shadow-lg transition-shadow"
              >
                <div
                  className={`w-14 h-14 ${f.color} rounded-xl flex items-center justify-center mb-5`}
                >
                  {f.icon}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  {f.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              How it works
            </h2>
          </div>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              {
                step: "1",
                title: "Register & Verify",
                desc: "Create your vendor profile with KYC, GST, and financial details",
              },
              {
                step: "2",
                title: "Upload Invoices",
                desc: "Create invoices for fulfilled orders directly in the platform",
              },
              {
                step: "3",
                title: "Get Risk Score",
                desc: "AI evaluates your profile and invoice for lender confidence",
              },
              {
                step: "4",
                title: "Receive Funding",
                desc: "Get 70-80% of invoice value as instant working capital",
              },
            ].map((s, i) => (
              <div key={i} className="text-center">
                <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-4">
                  {s.step}
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {s.title}
                </h3>
                <p className="text-gray-600 text-sm">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Checklist */}
      <section className="py-20 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            What you need to register
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {[
              "Personal PAN Card",
              "Personal Aadhaar Card",
              "GST Registration (GSTIN)",
              "CIBIL Score",
              "Business Registration Details",
              "Bank Account Details",
              "Electricity Bill (Address Proof)",
              "UDYAM Registration (if available)",
              "Business PAN Card",
              "Nominee Details",
            ].map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
              >
                <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                <span className="text-gray-700">{item}</span>
              </div>
            ))}
          </div>
          <div className="text-center mt-10">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-8 py-3.5 rounded-xl text-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              Start Registration <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">
              Invo<span className="text-blue-400">X</span>
            </span>
          </div>
          <p className="text-sm">
            &copy; 2026 InvoX. Embedded Invoice Financing for MSMEs.
          </p>
        </div>
      </footer>
    </div>
  );
}
