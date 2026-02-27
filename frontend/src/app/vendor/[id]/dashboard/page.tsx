"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, Loader2, IndianRupee, TrendingUp, AlertCircle, AlertTriangle,
  CheckCircle, Clock, Store, BarChart3, Receipt, Activity, Bell, Upload,
  Plus, Eye, BadgeCheck, ShieldCheck,
  Briefcase, CreditCard, ArrowRight, Sparkles, RefreshCw,
  Building2, Users, Percent,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import api, { getErrorMessage } from "@/lib/api";
import { VendorDashboardData, NotificationItem } from "@/lib/types";

const PIE_COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#64748b"];

// ─── Post-login Document Verification Banner ───
const POST_LOGIN_DOCS = [
  { key: "bank_statement", label: "Bank Statement (6 months)", vendorKey: "bank_statement_doc" },
  { key: "registration_certificate", label: "Registration Certificate", vendorKey: "registration_certificate_doc" },
];

function DocumentVerificationBanner({ vendorId }: { vendorId: string }) {
  const [vendor, setVendor] = useState<Record<string, unknown> | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    api.get(`/vendors/${vendorId}`).then(r => setVendor(r.data)).catch(() => {});
  }, [vendorId]);

  if (!vendor || dismissed) return null;

  const missingDocs = POST_LOGIN_DOCS.filter(d => !vendor[d.vendorKey]);
  if (missingDocs.length === 0) return null;

  const handleUpload = async (docType: string, file: File) => {
    setUploading(docType);
    const storedUser = localStorage.getItem("invox_user");
    const email = storedUser ? JSON.parse(storedUser).email : "";
    const formData = new FormData();
    formData.append("file", file);
    formData.append("email", email);
    formData.append("doc_type", docType);
    formData.append("stage", "post_login");
    try {
      await api.post("/auth/upload-document", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`${docType.replace("_", " ")} uploaded!`);
      // Refresh vendor data
      const r = await api.get(`/vendors/${vendorId}`);
      setVendor(r.data);
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploading(null);
    }
  };

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-amber-800">Complete Your Verification</h3>
            <p className="text-xs text-amber-600 mt-0.5">
              Upload the remaining documents to fully verify your account and unlock all features.
            </p>
          </div>
        </div>
        <button onClick={() => setDismissed(true)} className="text-amber-400 hover:text-amber-600 text-xs">Dismiss</button>
      </div>
      <div className="mt-4 space-y-2">
        {missingDocs.map(doc => (
          <div key={doc.key} className="flex items-center justify-between p-3 bg-white rounded-xl border border-amber-100">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <span className="text-sm text-gray-700 font-medium">{doc.label}</span>
            </div>
            <label className="cursor-pointer">
              <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(doc.key, f); }} />
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-100 text-amber-700 rounded-lg text-xs font-semibold hover:bg-amber-200 transition-colors">
                {uploading === doc.key ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
                Upload Now
              </span>
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function VendorDashboard() {
  const params = useParams();
  const vendorId = params.id as string;
  const [data, setData] = useState<VendorDashboardData | null>(null);
  const [notifs, setNotifs] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showNotifs, setShowNotifs] = useState(false);
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
              { label: "Repayments", href: `/vendor/${vendorId}/repayments` },
              { label: "Messages", href: "/chat" },
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
            <div className="relative">
              <button onClick={() => setShowNotifs(!showNotifs)} className="relative p-2 hover:bg-gray-50 rounded-xl transition-colors">
                <Bell className="w-5 h-5 text-gray-400" />
                {unread > 0 && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[9px] flex items-center justify-center font-bold">{unread}</span>
                )}
              </button>
              {showNotifs && (
                <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-2xl shadow-2xl border border-gray-100 z-[100] overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                    <h3 className="text-sm font-bold text-gray-900">Notifications</h3>
                    {unread > 0 && <span className="px-2 py-0.5 bg-red-50 text-red-600 rounded-lg text-[10px] font-semibold">{unread} new</span>}
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {notifs.length > 0 ? notifs.slice(0, 8).map((n) => (
                      <div key={n.id} className={`px-4 py-3 border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors ${!n.is_read ? "bg-indigo-50/40" : ""}`}>
                        <div className="flex items-start gap-2">
                          <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${n.is_read ? "bg-gray-300" : "bg-indigo-500"}`} />
                          <div className="min-w-0">
                            <p className="text-xs font-semibold text-gray-800 truncate">{n.title}</p>
                            <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-2">{n.message}</p>
                            {n.created_at && <p className="text-[10px] text-gray-400 mt-1">{new Date(n.created_at).toLocaleString("en-IN")}</p>}
                          </div>
                        </div>
                      </div>
                    )) : (
                      <div className="text-center py-8">
                        <Bell className="w-6 h-6 text-gray-200 mx-auto mb-2" />
                        <p className="text-xs text-gray-400">No notifications yet</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-bold">{data.vendor.name.charAt(0)}</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">
        {/* ─── Hero Welcome ─── */}
        <div className="relative bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 rounded-2xl p-6 text-white overflow-hidden">
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
                <Link href={`/vendor/${vendorId}/repayments`}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-white/15 backdrop-blur-sm text-white border border-white/20 rounded-xl text-xs font-semibold hover:bg-white/25 transition-all active:scale-[0.98]">
                  <CreditCard className="w-4 h-4" /> Repayments
                </Link>
              </div>
            </div>

            {/* Hero stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4">
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-4">
                <p className="text-indigo-200 text-[11px] uppercase tracking-wider font-medium mb-1">Total Invoices</p>
                <p className="text-2xl font-bold">{data.invoices.total}</p>
                <p className="text-indigo-300 text-[10px] mt-0.5">₹{data.invoices.total_value.toLocaleString("en-IN")} value</p>
              </div>
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-4">
                <p className="text-indigo-200 text-[11px] uppercase tracking-wider font-medium mb-1">Total Funded</p>
                <p className="text-2xl font-bold">₹{(data.marketplace.total_funded / 1000).toFixed(0)}K</p>
                <p className="text-indigo-300 text-[10px] mt-0.5">{data.marketplace.funded_count} deals</p>
              </div>
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-4">
                <p className="text-indigo-200 text-[11px] uppercase tracking-wider font-medium mb-1">Marketplace</p>
                <p className="text-2xl font-bold">{data.marketplace.total_listings}</p>
                <p className="text-indigo-300 text-[10px] mt-0.5">{data.marketplace.open} open listings</p>
              </div>
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-2xl p-4">
                <p className="text-indigo-200 text-[11px] uppercase tracking-wider font-medium mb-1">Repayments</p>
                <p className="text-2xl font-bold">₹{(data.repayment.paid_amount / 1000).toFixed(0)}K</p>
                <p className="text-indigo-300 text-[10px] mt-0.5">₹{(data.repayment.pending_amount / 1000).toFixed(0)}K pending</p>
              </div>
            </div>
          </div>
        </div>

        {/* ─── Document Verification Banner ─── */}
        <DocumentVerificationBanner vendorId={vendorId} />

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
        <div className="grid lg:grid-cols-3 gap-4">
          {/* Monthly Trend — 2/3 */}
          <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-indigo-500" /> Monthly Trend
              </h2>
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">Last 6 months</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
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
              <ResponsiveContainer width="100%" height={220}>
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
              <div className="flex flex-col items-center justify-center h-[220px] text-gray-400">
                <Receipt className="w-10 h-10 text-gray-200 mb-2" />
                <p className="text-sm">No invoices yet</p>
                <Link href={`/vendor/${vendorId}/invoices/create`}
                  className="mt-3 text-xs text-indigo-600 hover:underline">Create your first invoice →</Link>
              </div>
            )}
          </div>
        </div>



        {/* ─── Recent Activity ─── */}
        <div className="grid grid-cols-1 gap-4">
          <div className="bg-white rounded-2xl border border-gray-100 p-6">
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
              <div className="text-center py-6">
                <Activity className="w-8 h-8 text-gray-200 mx-auto mb-2" />
                <p className="text-sm text-gray-400">No recent activity</p>
                <p className="text-[11px] text-gray-300 mt-1">Activity will appear here as you use InvoX</p>
              </div>
            )}
          </div>
        </div>

        {/* ─── Quick Actions ─── */}
        <div className="grid grid-cols-3 lg:grid-cols-5 gap-3">
          {[
            { icon: Plus, label: "Create Invoice", desc: "Generate a new GST invoice", href: `/vendor/${vendorId}/invoices/create`, gradient: "from-indigo-500 to-violet-600" },
            { icon: Eye, label: "View Invoices", desc: "Manage your invoices", href: `/vendor/${vendorId}/invoices`, gradient: "from-blue-500 to-cyan-600" },
            { icon: CreditCard, label: "Repayments", desc: "Pay your installments", href: `/vendor/${vendorId}/repayments`, gradient: "from-emerald-500 to-teal-600" },
            { icon: Briefcase, label: "Marketplace", desc: "Browse & manage listings", href: "/marketplace", gradient: "from-purple-500 to-pink-600" },
            { icon: Activity, label: "AI Negotiations", desc: "View lender negotiations", href: `/vendor/${vendorId}/negotiations`, gradient: "from-violet-500 to-purple-700" },
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
