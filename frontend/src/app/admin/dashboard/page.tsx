"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, Loader2, Users, Building2, IndianRupee, AlertTriangle,
  CheckCircle, Clock, Store, Receipt, TrendingUp, Shield, Activity,
  ChevronDown, ChevronUp, AlertCircle, Bell,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";

interface OverviewData {
  users: { total: number; vendors: number; verified_vendors: number; lenders: number };
  invoices: { total: number; total_value: number; paid: number };
  marketplace: { total_listings: number; funded: number; settled: number; total_funded_amount: number };
  repayments: { total_due: number; total_paid: number; overdue_installments: number };
}

interface VendorRow {
  id: number;
  name: string;
  business_name: string;
  email: string;
  phone: string;
  gstin: string;
  profile_status: string;
  risk_score: number | null;
  cibil_score: number | null;
  total_owed: number;
  overdue_installments: number;
}

interface DefaultEntry {
  vendor_id: number;
  vendor_name: string;
  business_name: string;
  phone: string;
  email: string;
  risk_score: number | null;
  overdue_amount: number;
  overdue_installments: { id: number; listing_id: number; installment_number: number; due_date: string; total_amount: number }[];
}

type Tab = "overview" | "vendors" | "defaults";

export default function AdminDashboard() {
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [vendors, setVendors] = useState<VendorRow[]>([]);
  const [defaults, setDefaults] = useState<DefaultEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [ovRes, vRes, dRes] = await Promise.all([
        api.get("/admin/overview"),
        api.get("/admin/vendors"),
        api.get("/admin/defaults"),
      ]);
      setOverview(ovRes.data);
      setVendors(vRes.data);
      setDefaults(dRes.data);
    } catch (err) {
      toast.error(getErrorMessage(err, "Failed to load admin data"));
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAction = async (vendorId: number, action: string, note?: string) => {
    setActionLoading(vendorId);
    try {
      const r = await api.post(`/admin/vendor/${vendorId}/action`, { action, note: note || "" });
      toast.success(r.data.message);
      fetchData();
    } catch (err) {
      toast.error(getErrorMessage(err, "Action failed"));
    }
    setActionLoading(null);
  };

  const tabs: { key: Tab; label: string; icon: typeof Users }[] = [
    { key: "overview", label: "Overview", icon: TrendingUp },
    { key: "vendors", label: "Vendors", icon: Building2 },
    { key: "defaults", label: "Defaults & Overdue", icon: AlertTriangle },
  ];

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-[#f8f9fc]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-red-600 to-rose-600 rounded-xl flex items-center justify-center shadow-lg shadow-red-200">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">Invo<span className="text-red-600">X</span> <span className="text-xs text-gray-400 font-normal">Admin</span></span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/marketplace" className="text-xs text-gray-500 hover:text-gray-700">Marketplace</Link>
            <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
              <span className="text-red-700 text-xs font-bold">A</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Title */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Monitor platform activity, manage vendors, and handle defaults</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-white rounded-xl border border-gray-100 p-1 w-fit">
          {tabs.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                tab === t.key ? "bg-red-50 text-red-700" : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}>
              <t.icon className="w-3.5 h-3.5" /> {t.label}
              {t.key === "defaults" && defaults.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 bg-red-500 text-white rounded-full text-[9px] font-bold">{defaults.length}</span>
              )}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-10 h-10 text-red-600 animate-spin" />
          </div>
        ) : (
          <>
            {/* ─── OVERVIEW TAB ─── */}
            {tab === "overview" && overview && (
              <div className="space-y-6">
                {/* KPI Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white rounded-2xl border border-gray-100 p-5">
                    <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center mb-3">
                      <Users className="w-5 h-5 text-blue-600" />
                    </div>
                    <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">Total Users</p>
                    <p className="text-2xl font-bold text-gray-900 mt-0.5">{overview.users.total}</p>
                    <p className="text-[11px] text-gray-400 mt-1">{overview.users.vendors} vendors · {overview.users.lenders} lenders</p>
                  </div>
                  <div className="bg-white rounded-2xl border border-gray-100 p-5">
                    <div className="w-10 h-10 bg-indigo-50 rounded-xl flex items-center justify-center mb-3">
                      <Receipt className="w-5 h-5 text-indigo-600" />
                    </div>
                    <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">Invoices</p>
                    <p className="text-2xl font-bold text-gray-900 mt-0.5">{overview.invoices.total}</p>
                    <p className="text-[11px] text-gray-400 mt-1">₹{overview.invoices.total_value.toLocaleString("en-IN")} total value</p>
                  </div>
                  <div className="bg-white rounded-2xl border border-gray-100 p-5">
                    <div className="w-10 h-10 bg-emerald-50 rounded-xl flex items-center justify-center mb-3">
                      <IndianRupee className="w-5 h-5 text-emerald-600" />
                    </div>
                    <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">Total Funded</p>
                    <p className="text-2xl font-bold text-emerald-700 mt-0.5">₹{overview.marketplace.total_funded_amount.toLocaleString("en-IN")}</p>
                    <p className="text-[11px] text-gray-400 mt-1">{overview.marketplace.funded} active · {overview.marketplace.settled} settled</p>
                  </div>
                  <div className="bg-white rounded-2xl border border-gray-100 p-5">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-3 ${
                      overview.repayments.overdue_installments > 0 ? "bg-red-50" : "bg-green-50"
                    }`}>
                      <AlertTriangle className={`w-5 h-5 ${
                        overview.repayments.overdue_installments > 0 ? "text-red-600" : "text-green-600"
                      }`} />
                    </div>
                    <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">Overdue</p>
                    <p className={`text-2xl font-bold mt-0.5 ${
                      overview.repayments.overdue_installments > 0 ? "text-red-700" : "text-green-700"
                    }`}>{overview.repayments.overdue_installments}</p>
                    <p className="text-[11px] text-gray-400 mt-1">installments overdue</p>
                  </div>
                </div>

                {/* Repayment Overview */}
                <div className="grid lg:grid-cols-2 gap-6">
                  <div className="bg-white rounded-2xl border border-gray-100 p-6">
                    <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2 mb-5">
                      <Store className="w-4 h-4 text-indigo-500" /> Marketplace Summary
                    </h2>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">Total Listings</span>
                        <span className="text-sm font-bold text-gray-900">{overview.marketplace.total_listings}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">Active (Funded)</span>
                        <span className="text-sm font-bold text-blue-600">{overview.marketplace.funded}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">Settled</span>
                        <span className="text-sm font-bold text-emerald-600">{overview.marketplace.settled}</span>
                      </div>
                      <div className="flex justify-between items-center border-t border-gray-100 pt-3">
                        <span className="text-xs text-gray-500">Verified Vendors</span>
                        <span className="text-sm font-bold text-gray-900">{overview.users.verified_vendors}/{overview.users.vendors}</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white rounded-2xl border border-gray-100 p-6">
                    <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2 mb-5">
                      <IndianRupee className="w-4 h-4 text-emerald-500" /> Repayment Tracker
                    </h2>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">Total Repayment Due</span>
                        <span className="text-sm font-bold text-gray-900">₹{overview.repayments.total_due.toLocaleString("en-IN")}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">Collected</span>
                        <span className="text-sm font-bold text-emerald-600">₹{overview.repayments.total_paid.toLocaleString("en-IN")}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-500">Outstanding</span>
                        <span className="text-sm font-bold text-amber-600">₹{(overview.repayments.total_due - overview.repayments.total_paid).toLocaleString("en-IN")}</span>
                      </div>
                      {overview.repayments.total_due > 0 && (
                        <div className="pt-2">
                          <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-emerald-500 to-green-500 rounded-full transition-all"
                              style={{ width: `${Math.min(100, (overview.repayments.total_paid / overview.repayments.total_due) * 100)}%` }} />
                          </div>
                          <p className="text-[10px] text-gray-400 mt-1 text-right">
                            {((overview.repayments.total_paid / overview.repayments.total_due) * 100).toFixed(1)}% collected
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ─── VENDORS TAB ─── */}
            {tab === "vendors" && (
              <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-400 uppercase tracking-wider border-b border-gray-100 bg-gray-50">
                        <th className="px-4 py-3 text-left font-medium">Vendor</th>
                        <th className="px-4 py-3 text-left font-medium">GSTIN</th>
                        <th className="px-4 py-3 text-center font-medium">Status</th>
                        <th className="px-4 py-3 text-center font-medium">CIBIL</th>
                        <th className="px-4 py-3 text-center font-medium">Risk</th>
                        <th className="px-4 py-3 text-right font-medium">Owed</th>
                        <th className="px-4 py-3 text-center font-medium">Overdue</th>
                        <th className="px-4 py-3 text-center font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendors.map((v) => (
                        <tr key={v.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                          <td className="px-4 py-3.5">
                            <p className="font-semibold text-gray-900">{v.name}</p>
                            <p className="text-gray-400 text-[10px]">{v.business_name}</p>
                          </td>
                          <td className="px-4 py-3.5 text-gray-600 font-mono text-[10px]">{v.gstin}</td>
                          <td className="px-4 py-3.5 text-center">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-semibold ${
                              v.profile_status === "verified" ? "bg-emerald-50 text-emerald-700" :
                              v.profile_status === "suspended" ? "bg-red-50 text-red-700" :
                              "bg-yellow-50 text-yellow-700"
                            }`}>
                              {v.profile_status === "verified" ? <CheckCircle className="w-3 h-3" /> :
                               v.profile_status === "suspended" ? <AlertCircle className="w-3 h-3" /> :
                               <Clock className="w-3 h-3" />}
                              {v.profile_status}
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-center font-semibold">{v.cibil_score ?? "—"}</td>
                          <td className="px-4 py-3.5 text-center">
                            <span className={`font-semibold ${
                              (v.risk_score ?? 50) <= 40 ? "text-green-600" :
                              (v.risk_score ?? 50) <= 60 ? "text-yellow-600" : "text-red-600"
                            }`}>{v.risk_score ?? "—"}</span>
                          </td>
                          <td className="px-4 py-3.5 text-right font-semibold text-gray-700">
                            {v.total_owed > 0 ? `₹${v.total_owed.toLocaleString("en-IN")}` : "—"}
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            {v.overdue_installments > 0 ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-50 text-red-700 rounded-lg text-[10px] font-bold">
                                <AlertTriangle className="w-3 h-3" /> {v.overdue_installments}
                              </span>
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            <div className="flex items-center justify-center gap-1">
                              {v.profile_status !== "suspended" && v.overdue_installments > 0 && (
                                <button onClick={() => handleAction(v.id, "warn", "Overdue payment reminder")}
                                  disabled={actionLoading === v.id}
                                  className="px-2.5 py-1 bg-amber-50 text-amber-700 rounded-lg text-[10px] font-semibold hover:bg-amber-100 disabled:opacity-50">
                                  Warn
                                </button>
                              )}
                              {v.profile_status === "verified" && (
                                <button onClick={() => handleAction(v.id, "suspend", "Multiple overdue payments")}
                                  disabled={actionLoading === v.id}
                                  className="px-2.5 py-1 bg-red-50 text-red-700 rounded-lg text-[10px] font-semibold hover:bg-red-100 disabled:opacity-50">
                                  Suspend
                                </button>
                              )}
                              {v.profile_status === "suspended" && (
                                <button onClick={() => handleAction(v.id, "approve", "Reinstated by admin")}
                                  disabled={actionLoading === v.id}
                                  className="px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-[10px] font-semibold hover:bg-emerald-100 disabled:opacity-50">
                                  Reinstate
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {vendors.length === 0 && (
                  <div className="text-center py-12 text-gray-400">
                    <Users className="w-10 h-10 mx-auto mb-2 text-gray-200" />
                    <p className="text-sm">No vendors registered yet</p>
                  </div>
                )}
              </div>
            )}

            {/* ─── DEFAULTS TAB ─── */}
            {tab === "defaults" && (
              <div className="space-y-4">
                {defaults.length === 0 ? (
                  <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
                    <div className="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <CheckCircle className="w-8 h-8 text-emerald-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">No Defaults</h3>
                    <p className="text-sm text-gray-500">All vendors are up to date with their repayments.</p>
                  </div>
                ) : (
                  defaults.map((d) => (
                    <div key={d.vendor_id} className="bg-white rounded-2xl border border-red-100 overflow-hidden">
                      <div className="p-5 bg-red-50/50">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
                              <AlertTriangle className="w-6 h-6 text-red-600" />
                            </div>
                            <div>
                              <h3 className="text-sm font-bold text-gray-900">{d.vendor_name}</h3>
                              <p className="text-xs text-gray-500">{d.business_name} · {d.phone}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-lg font-bold text-red-700">₹{d.overdue_amount.toLocaleString("en-IN")}</p>
                            <p className="text-[10px] text-red-500">{d.overdue_installments.length} overdue installment{d.overdue_installments.length !== 1 ? "s" : ""}</p>
                          </div>
                        </div>
                      </div>
                      <div className="px-5 pb-4">
                        <table className="w-full text-xs mt-3">
                          <thead>
                            <tr className="text-gray-400 border-b border-gray-100">
                              <th className="py-2 text-left font-medium">Listing</th>
                              <th className="py-2 text-left font-medium">Installment</th>
                              <th className="py-2 text-left font-medium">Due Date</th>
                              <th className="py-2 text-right font-medium">Amount</th>
                            </tr>
                          </thead>
                          <tbody>
                            {d.overdue_installments.map((inst) => (
                              <tr key={inst.id} className="border-b border-gray-50">
                                <td className="py-2 text-gray-700">#{inst.listing_id}</td>
                                <td className="py-2 text-gray-700">#{inst.installment_number}</td>
                                <td className="py-2 text-red-600 font-semibold">{new Date(inst.due_date).toLocaleDateString("en-IN")}</td>
                                <td className="py-2 text-right font-bold text-gray-900">₹{inst.total_amount.toLocaleString("en-IN")}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        <div className="flex gap-2 mt-4">
                          <button onClick={() => handleAction(d.vendor_id, "warn", "Overdue payment — urgent reminder")}
                            disabled={actionLoading === d.vendor_id}
                            className="px-4 py-2 bg-amber-600 text-white rounded-lg text-xs font-semibold hover:bg-amber-700 disabled:opacity-50">
                            {actionLoading === d.vendor_id ? <Loader2 className="w-3 h-3 animate-spin inline mr-1" /> : null}
                            Send Warning
                          </button>
                          <button onClick={() => handleAction(d.vendor_id, "suspend", "Suspended due to overdue payments")}
                            disabled={actionLoading === d.vendor_id}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-semibold hover:bg-red-700 disabled:opacity-50">
                            Suspend Vendor
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
    </ProtectedRoute>
  );
}
