"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, Loader2, IndianRupee, TrendingUp, ShieldCheck, AlertCircle,
  CheckCircle, Clock, Store, BarChart3, Receipt, Activity, Bell,
  Plus, ArrowUpRight, Gauge, BadgeCheck, AlertTriangle, Eye,
  Briefcase, CreditCard, ArrowRight, Sparkles, Shield, RefreshCw,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import api, { getErrorMessage } from "@/lib/api";
import { VendorDashboardData, NotificationItem } from "@/lib/types";

const PIE_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#64748b"];

const riskMeter = (score: number | null) => {
  const s = score ?? 50;
  if (s <= 25) return { label: "Very Low", color: "text-emerald-600", bg: "bg-emerald-500", fill: "from-emerald-400 to-emerald-600" };
  if (s <= 40) return { label: "Low", color: "text-green-600", bg: "bg-green-500", fill: "from-green-400 to-green-600" };
  if (s <= 55) return { label: "Moderate", color: "text-yellow-600", bg: "bg-yellow-500", fill: "from-yellow-400 to-yellow-600" };
  if (s <= 70) return { label: "High", color: "text-orange-600", bg: "bg-orange-500", fill: "from-orange-400 to-orange-600" };
  return { label: "Very High", color: "text-red-600", bg: "bg-red-500", fill: "from-red-400 to-red-600" };
};

const cibilGrade = (score: number | null) => {
  if (!score) return { grade: "N/A", color: "text-gray-400", bg: "bg-gray-100" };
  if (score >= 750) return { grade: "Excellent", color: "text-emerald-700", bg: "bg-emerald-50" };
  if (score >= 700) return { grade: "Good", color: "text-green-700", bg: "bg-green-50" };
  if (score >= 650) return { grade: "Fair", color: "text-yellow-700", bg: "bg-yellow-50" };
  return { grade: "Poor", color: "text-red-700", bg: "bg-red-50" };
};

export default function VendorDashboard() {
  const params = useParams();
  const vendorId = params.id as string;
  const [data, setData] = useState<VendorDashboardData | null>(null);
  const [notifs, setNotifs] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = () => {
    setLoading(true);
    setError(null);
    api.get(`/dashboard/vendor/${vendorId}`)
      .then((r) => { setData(r.data); setLoading(false); })
      .catch((err) => {
        const msg = getErrorMessage(err, "Failed to load dashboard");
        setError(msg);
        setLoading(false);
        toast.error(msg);
      });
  };

  useEffect(() => {
    fetchDashboard();

    const storedUser = localStorage.getItem("invox_user");
    if (storedUser) {
      const user = JSON.parse(storedUser);
      api.get(`/notifications/${user.id}`).then((r) => setNotifs(r.data)).catch(() => {});
      api.get(`/notifications/${user.id}/unread-count`).then((r) => setUnread(r.data.unread)).catch(() => {});
    }
  }, [vendorId]);

  if (loading) return (
    <div className="min-h-screen bg-[#f8f9fc] flex items-center justify-center">
      <div className="text-center">
        <div className="relative inline-block">
          <div className="w-16 h-16 border-4 border-indigo-100 rounded-full" />
          <div className="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin absolute inset-0" />
        </div>
        <p className="text-sm text-gray-500 mt-4">Loading your dashboard...</p>
      </div>
    </div>
  );

  if (!data) return (
    <div className="min-h-screen bg-[#f8f9fc] flex items-center justify-center">
      <div className="text-center max-w-sm">
        <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="w-8 h-8 text-red-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-1">Dashboard Unavailable</h3>
        <p className="text-sm text-gray-500 mb-4">{error || "Could not load your dashboard data. Please try again."}</p>
        <button onClick={fetchDashboard}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors">
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    </div>
  );

  const statusPieData = Object.entries(data.invoices.status_distribution).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1).replace("_", " "),
    value,
  }));

  const verifPct = data.verification.total_checks > 0
    ? Math.round((data.verification.passed / data.verification.total_checks) * 100)
    : 0;

  const risk = riskMeter(data.vendor.risk_score);
  const cibil = cibilGrade(data.vendor.cibil_score);

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
  };

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-[#f8f9fc]">
      {/* ─── Sticky Header ─── */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">Invo<span className="text-indigo-600">X</span></span>
          </Link>
          <nav className="hidden sm:flex items-center gap-1">
            {[
              { label: "Dashboard", href: `/vendor/${vendorId}/dashboard`, active: true },
              { label: "Invoices", href: `/vendor/${vendorId}/invoices` },
              { label: "Verification", href: `/vendor/${vendorId}/verify` },
              { label: "Marketplace", href: "/marketplace" },
              { label: "Profile", href: `/vendor/${vendorId}` },
            ].map((nav) => (
              <Link key={nav.label} href={nav.href}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  nav.active
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                }`}>
                {nav.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <button className="relative p-2 hover:bg-gray-50 rounded-xl transition-colors">
              <Bell className="w-5 h-5 text-gray-400" />
              {unread > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[9px] flex items-center justify-center font-bold">{unread}</span>
              )}
            </button>
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-bold">{data.vendor.name.charAt(0)}</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* ─── Hero Welcome ─── */}
        <div className="relative bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 rounded-3xl p-8 text-white overflow-hidden">
          {/* Pattern overlay */}
          <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }} />
          <div className="relative z-10">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <p className="text-indigo-200 text-sm mb-1">{greeting()}</p>
                <h1 className="text-2xl sm:text-3xl font-bold">{data.vendor.name}</h1>
                <p className="text-indigo-200 text-sm mt-1">{data.vendor.business_name}</p>
                <div className="flex items-center gap-3 mt-4">
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-[11px] font-semibold backdrop-blur-sm ${
                    data.vendor.profile_status === "verified"
                      ? "bg-emerald-400/20 text-emerald-200 border border-emerald-400/30"
                      : "bg-yellow-400/20 text-yellow-200 border border-yellow-400/30"
                  }`}>
                    {data.vendor.profile_status === "verified" ? <BadgeCheck className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
                    {data.vendor.profile_status === "verified" ? "Verified" : "Pending Verification"}
                  </span>
                </div>
              </div>
              <div className="flex gap-3">
                <Link href={`/vendor/${vendorId}/invoices/create`}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-indigo-700 rounded-xl text-xs font-semibold hover:bg-indigo-50 transition-all active:scale-[0.98] shadow-lg">
                  <Plus className="w-4 h-4" /> Create Invoice
                </Link>
                <Link href={`/vendor/${vendorId}/verify`}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-white/15 backdrop-blur-sm text-white border border-white/20 rounded-xl text-xs font-semibold hover:bg-white/25 transition-all active:scale-[0.98]">
                  <ShieldCheck className="w-4 h-4" /> Verify Profile
                </Link>
              </div>
            </div>

            {/* Hero stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-4">
                <p className="text-indigo-200 text-[11px] uppercase tracking-wider font-medium mb-1">CIBIL Score</p>
                <p className="text-2xl font-bold">{data.vendor.cibil_score ?? "—"}</p>
                <p className="text-indigo-300 text-[10px] mt-0.5">{cibil.grade}</p>
              </div>
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-4">
                <p className="text-indigo-200 text-[11px] uppercase tracking-wider font-medium mb-1">Risk Score</p>
                <p className="text-2xl font-bold">{data.vendor.risk_score ?? "—"}<span className="text-sm font-normal text-indigo-300">/100</span></p>
                <p className="text-indigo-300 text-[10px] mt-0.5">{risk.label}</p>
              </div>
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-4">
                <p className="text-indigo-200 text-[11px] uppercase tracking-wider font-medium mb-1">Total Funded</p>
                <p className="text-2xl font-bold">₹{(data.marketplace.total_funded / 1000).toFixed(0)}K</p>
                <p className="text-indigo-300 text-[10px] mt-0.5">{data.marketplace.funded_count} deals</p>
              </div>
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-4">
                <p className="text-indigo-200 text-[11px] uppercase tracking-wider font-medium mb-1">Verification</p>
                <p className="text-2xl font-bold">{verifPct}%</p>
                <p className="text-indigo-300 text-[10px] mt-0.5">{data.verification.passed}/{data.verification.total_checks} passed</p>
              </div>
            </div>
          </div>
        </div>

        {/* ─── KPI Cards ─── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              icon: Receipt, label: "Total Invoices", value: data.invoices.total.toString(),
              sub: `₹${data.invoices.total_value.toLocaleString("en-IN")} value`,
              color: "text-indigo-600", iconBg: "bg-indigo-50",
              badge: data.invoices.draft > 0 ? `${data.invoices.draft} draft` : null,
              badgeColor: "bg-yellow-50 text-yellow-700",
            },
            {
              icon: Store, label: "Marketplace", value: data.marketplace.total_listings.toString(),
              sub: `${data.marketplace.open} open · ${data.marketplace.funded_count} funded`,
              color: "text-violet-600", iconBg: "bg-violet-50",
              badge: data.marketplace.open > 0 ? `${data.marketplace.open} active` : null,
              badgeColor: "bg-emerald-50 text-emerald-700",
            },
            {
              icon: IndianRupee, label: "Funded Amount", value: `₹${data.marketplace.total_funded.toLocaleString("en-IN")}`,
              sub: `₹${data.marketplace.total_settled.toLocaleString("en-IN")} settled`,
              color: "text-emerald-600", iconBg: "bg-emerald-50",
              badge: null, badgeColor: "",
            },
            {
              icon: CreditCard, label: "Pending Repayment", value: `₹${data.repayment.pending_amount.toLocaleString("en-IN")}`,
              sub: `₹${data.repayment.paid_amount.toLocaleString("en-IN")} paid`,
              color: "text-amber-600", iconBg: "bg-amber-50",
              badge: data.repayment.overdue_installments > 0 ? `${data.repayment.overdue_installments} overdue` : null,
              badgeColor: "bg-red-50 text-red-700",
            },
          ].map((card) => (
            <div key={card.label} className="bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-md hover:shadow-gray-100/50 transition-all group">
              <div className="flex items-start justify-between mb-3">
                <div className={`w-10 h-10 ${card.iconBg} rounded-xl flex items-center justify-center`}>
                  <card.icon className={`w-5 h-5 ${card.color}`} />
                </div>
                {card.badge && (
                  <span className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold ${card.badgeColor}`}>{card.badge}</span>
                )}
              </div>
              <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">{card.label}</p>
              <p className={`text-2xl font-bold text-gray-900 mt-1`}>{card.value}</p>
              <p className="text-[11px] text-gray-400 mt-1">{card.sub}</p>
            </div>
          ))}
        </div>

        {/* ─── Charts Row ─── */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Monthly Trend — 2/3 */}
          <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-indigo-500" /> Monthly Trend
              </h2>
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">Last 6 months</span>
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.monthly_trend} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
                <Tooltip
                  formatter={(val) => `₹${Number(val).toLocaleString("en-IN")}`}
                  contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 4px 12px rgba(0,0,0,0.08)", fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                <Bar dataKey="invoice_value" name="Invoice Value" fill="#6366f1" radius={[6, 6, 0, 0]} />
                <Bar dataKey="funded" name="Funded" fill="#22c55e" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Invoice Status Pie — 1/3 */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2 mb-5">
              <TrendingUp className="w-4 h-4 text-violet-500" /> Invoice Status
            </h2>
            {statusPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie data={statusPieData} cx="50%" cy="45%" innerRadius={55} outerRadius={85}
                    paddingAngle={4} dataKey="value" stroke="none"
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={false}>
                    {statusPieData.map((_, idx) => (
                      <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-[260px] text-gray-400">
                <Receipt className="w-10 h-10 text-gray-200 mb-2" />
                <p className="text-sm">No invoices yet</p>
                <Link href={`/vendor/${vendorId}/invoices/create`}
                  className="mt-3 text-xs text-indigo-600 hover:underline">Create your first invoice →</Link>
              </div>
            )}
          </div>
        </div>

        {/* ─── Risk & Verification Row ─── */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Risk Assessment */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2 mb-5">
              <Gauge className="w-4 h-4 text-indigo-500" /> Risk Assessment
            </h2>
            <div className="flex items-start gap-6">
              {/* Risk gauge */}
              <div className="flex-shrink-0">
                <div className="relative w-28 h-28">
                  <svg className="w-28 h-28 -rotate-90" viewBox="0 0 36 36">
                    <circle cx="18" cy="18" r="14" fill="none" stroke="#f1f5f9" strokeWidth="4" />
                    <circle cx="18" cy="18" r="14" fill="none" strokeWidth="4" strokeLinecap="round"
                      className={`${risk.bg.replace("bg-", "stroke-")}`}
                      strokeDasharray={`${(data.vendor.risk_score ?? 50) * 0.88} ${88 - (data.vendor.risk_score ?? 50) * 0.88}`} />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className={`text-2xl font-bold ${risk.color}`}>{data.vendor.risk_score ?? "—"}</span>
                    <span className="text-[9px] text-gray-400">/100</span>
                  </div>
                </div>
              </div>
              <div className="flex-1 space-y-3">
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-bold ${risk.color}`}>{risk.label} Risk</span>
                </div>
                <div className="space-y-2">
                  {[
                    { label: "CIBIL Score", value: `${data.vendor.cibil_score ?? "—"} (${cibil.grade})`, weight: "40%" },
                    { label: "Profile Status", value: data.vendor.profile_status, weight: "10%" },
                  ].map((f) => (
                    <div key={f.label} className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">{f.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-700 capitalize">{f.value}</span>
                        <span className="text-[10px] text-gray-400">{f.weight}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="pt-2 border-t border-gray-100">
                  <p className="text-[11px] text-gray-400 flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> AI-computed composite score based on CIBIL, GST, age, financials & verification
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Verification Status */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-500" /> Verification Status
              </h2>
              <Link href={`/vendor/${vendorId}/verify`}
                className="text-[11px] text-indigo-600 hover:underline font-medium">Run checks →</Link>
            </div>
            <div className="flex items-center gap-6">
              <div className="relative w-28 h-28 flex-shrink-0">
                <svg className="w-28 h-28 -rotate-90" viewBox="0 0 36 36">
                  <circle cx="18" cy="18" r="14" fill="none" stroke="#f1f5f9" strokeWidth="4" />
                  <circle cx="18" cy="18" r="14" fill="none" stroke="#22c55e" strokeWidth="4"
                    strokeDasharray={`${verifPct * 0.88} ${88 - verifPct * 0.88}`} strokeLinecap="round" />
                </svg>
                <span className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold text-gray-900">{verifPct}%</span>
                  <span className="text-[9px] text-gray-400">passed</span>
                </span>
              </div>
              <div className="flex-1 grid grid-cols-2 gap-2">
                {[
                  { icon: CheckCircle, label: "Passed", count: data.verification.passed, color: "text-emerald-600", bg: "bg-emerald-50" },
                  { icon: AlertCircle, label: "Failed", count: data.verification.failed, color: "text-red-600", bg: "bg-red-50" },
                  { icon: AlertTriangle, label: "Warnings", count: data.verification.warning, color: "text-yellow-600", bg: "bg-yellow-50" },
                  { icon: Clock, label: "Pending", count: data.verification.pending, color: "text-gray-500", bg: "bg-gray-50" },
                ].map((item) => (
                  <div key={item.label} className={`${item.bg} rounded-xl p-3 text-center`}>
                    <item.icon className={`w-4 h-4 ${item.color} mx-auto mb-1`} />
                    <p className={`text-lg font-bold ${item.color}`}>{item.count}</p>
                    <p className="text-[10px] text-gray-500">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ─── Activity & Notifications ─── */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Recent Activity — 2/3 */}
          <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 p-6">
            <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2 mb-5">
              <Activity className="w-4 h-4 text-indigo-500" /> Recent Activity
            </h2>
            {data.recent_activity.length > 0 ? (
              <div className="space-y-0">
                {data.recent_activity.map((a, idx) => (
                  <div key={a.id} className="flex gap-3 py-3 border-b border-gray-50 last:border-0">
                    <div className="flex flex-col items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        a.action?.includes("fund") ? "bg-emerald-100" :
                        a.action?.includes("verif") ? "bg-blue-100" :
                        a.action?.includes("list") ? "bg-violet-100" :
                        a.action?.includes("invoice") || a.action?.includes("creat") ? "bg-indigo-100" :
                        "bg-gray-100"
                      }`}>
                        {a.action?.includes("fund") ? <IndianRupee className="w-4 h-4 text-emerald-600" /> :
                         a.action?.includes("verif") ? <ShieldCheck className="w-4 h-4 text-blue-600" /> :
                         a.action?.includes("list") ? <Store className="w-4 h-4 text-violet-600" /> :
                         <FileText className="w-4 h-4 text-indigo-600" />}
                      </div>
                      {idx < data.recent_activity.length - 1 && <div className="w-px h-full bg-gray-100 mt-1" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-900 capitalize">{a.action}</p>
                      <p className="text-[11px] text-gray-500 mt-0.5">{a.description}</p>
                      {a.created_at && (
                        <p className="text-[10px] text-gray-400 mt-1">{new Date(a.created_at).toLocaleString("en-IN")}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <Activity className="w-10 h-10 text-gray-200 mx-auto mb-2" />
                <p className="text-sm text-gray-400">No recent activity</p>
                <p className="text-[11px] text-gray-300 mt-1">Activity will appear here as you use InvoX</p>
              </div>
            )}
          </div>

          {/* Notifications — 1/3 */}
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <Bell className="w-4 h-4 text-red-500" /> Notifications
              </h2>
              {unread > 0 && (
                <span className="px-2 py-0.5 bg-red-50 text-red-600 rounded-lg text-[10px] font-semibold">{unread} new</span>
              )}
            </div>
            {notifs.length > 0 ? (
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {notifs.slice(0, 8).map((n) => (
                  <div key={n.id} className={`p-3 rounded-xl border transition-colors ${
                    n.is_read ? "bg-white border-gray-100" : "bg-indigo-50/50 border-indigo-100"
                  }`}>
                    <div className="flex items-start gap-2">
                      <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${n.is_read ? "bg-gray-300" : "bg-indigo-500"}`} />
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-gray-800 truncate">{n.title}</p>
                        <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-2">{n.message}</p>
                        {n.created_at && <p className="text-[10px] text-gray-400 mt-1">{new Date(n.created_at).toLocaleString("en-IN")}</p>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <Bell className="w-10 h-10 text-gray-200 mx-auto mb-2" />
                <p className="text-sm text-gray-400">No notifications</p>
              </div>
            )}
          </div>
        </div>

        {/* ─── Quick Actions ─── */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {[
            { icon: Plus, label: "Create Invoice", desc: "Generate a new GST invoice", href: `/vendor/${vendorId}/invoices/create`, gradient: "from-indigo-500 to-violet-600" },
            { icon: Eye, label: "View Invoices", desc: "Manage your invoices", href: `/vendor/${vendorId}/invoices`, gradient: "from-blue-500 to-cyan-600" },
            { icon: ShieldCheck, label: "Run Verification", desc: "Check compliance status", href: `/vendor/${vendorId}/verify`, gradient: "from-emerald-500 to-teal-600" },
            { icon: Shield, label: "KYC Verification", desc: "Complete identity check", href: "/kyc", gradient: "from-amber-500 to-orange-600" },
            { icon: Briefcase, label: "Marketplace", desc: "Browse & manage listings", href: "/marketplace", gradient: "from-purple-500 to-pink-600" },
          ].map((action) => (
            <Link key={action.label} href={action.href}
              className="group bg-white rounded-2xl border border-gray-100 p-5 hover:shadow-lg hover:shadow-gray-100/50 transition-all hover:-translate-y-0.5">
              <div className={`w-10 h-10 bg-gradient-to-br ${action.gradient} rounded-xl flex items-center justify-center mb-3 shadow-lg group-hover:scale-110 transition-transform`}>
                <action.icon className="w-5 h-5 text-white" />
              </div>
              <p className="text-sm font-bold text-gray-900">{action.label}</p>
              <p className="text-[11px] text-gray-400 mt-0.5">{action.desc}</p>
              <div className="flex items-center gap-1 mt-3 text-[11px] text-indigo-600 font-medium">
                Go <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
