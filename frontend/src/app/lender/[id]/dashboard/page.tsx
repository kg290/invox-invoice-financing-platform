"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText, Loader2, IndianRupee, TrendingUp, AlertCircle, Clock,
  Store, BarChart3, PieChart as PieIcon, Activity, Bell, Briefcase,
  ArrowUpRight, Wallet, Target, X, Check, ArrowDownToLine, Lock, Unlock,
  BanknoteIcon, ExternalLink, ChevronRight,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend,
} from "recharts";
import api from "@/lib/api";
import { LenderDashboardData, NotificationItem } from "@/lib/types";

const RISK_COLORS: Record<string, string> = { low: "#22c55e", medium: "#f59e0b", high: "#ef4444" };
const BIZ_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#22c55e", "#6b7280"];

export default function LenderDashboard() {
  const params = useParams();
  const router = useRouter();
  const lenderId = params.id as string;
  const [data, setData] = useState<LenderDashboardData | null>(null);
  const [notifs, setNotifs] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showNotifs, setShowNotifs] = useState(false);
  const [withdrawAmt, setWithdrawAmt] = useState("");
  const [showWithdraw, setShowWithdraw] = useState(false);
  const [withdrawing, setWithdrawing] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  const fetchDashboard = () => {
    api.get(`/dashboard/lender/${lenderId}`)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDashboard();

    const storedUser = localStorage.getItem("invox_user");
    if (storedUser) {
      const user = JSON.parse(storedUser);
      api.get(`/notifications/${user.id}`).then((r) => setNotifs(r.data)).catch(() => {});
      api.get(`/notifications/${user.id}/unread-count`).then((r) => setUnread(r.data.unread)).catch(() => {});
    }
  }, [lenderId]);

  // Close notification dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setShowNotifs(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const markNotifRead = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await api.patch(`/notifications/${notif.id}/read`);
        setNotifs((prev) => prev.map((n) => n.id === notif.id ? { ...n, is_read: true } : n));
        setUnread((u) => Math.max(0, u - 1));
      } catch {}
    }
    if (notif.link) {
      setShowNotifs(false);
      router.push(notif.link);
    }
  };

  const markAllRead = async () => {
    const storedUser = localStorage.getItem("invox_user");
    if (!storedUser) return;
    const user = JSON.parse(storedUser);
    try {
      await api.patch(`/notifications/read-all/${user.id}`);
      setNotifs((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnread(0);
    } catch {}
  };

  const handleWithdraw = async () => {
    const amt = parseFloat(withdrawAmt);
    if (!amt || amt <= 0) return;
    setWithdrawing(true);
    try {
      await api.post("/marketplace/lender/wallet/withdraw", { lender_id: Number(lenderId), amount: amt });
      setShowWithdraw(false);
      setWithdrawAmt("");
      fetchDashboard();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Withdrawal failed";
      alert(msg);
    }
    setWithdrawing(false);
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
    </div>
  );
  if (!data) return (
    <div className="min-h-screen flex items-center justify-center flex-col gap-2">
      <AlertCircle className="w-10 h-10 text-red-400" />
      <p className="text-gray-600">Dashboard data not available</p>
    </div>
  );

  const riskPie = Object.entries(data.risk_distribution).map(([name, value]) => ({ name, value }));
  const bizPie = Object.entries(data.business_type_distribution).map(([name, value]) => ({ name, value }));
  const wallet = data.wallet || { balance: 0, escrow_locked: 0, total_withdrawn: 0 };

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-14">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-purple-600 to-indigo-700 rounded-lg flex items-center justify-center">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">Invo<span className="text-purple-600">X</span></span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/chat" className="text-xs text-gray-500 hover:text-gray-700">Messages</Link>
            <Link href="/marketplace" className="text-xs text-gray-500 hover:text-gray-700">Marketplace</Link>
            {/* Notification Bell — Clickable dropdown */}
            <div className="relative" ref={notifRef}>
              <button onClick={() => setShowNotifs(!showNotifs)} className="relative p-1 hover:bg-gray-100 rounded-lg transition-colors">
                <Bell className="w-5 h-5 text-gray-400" />
                {unread > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[10px] flex items-center justify-center font-bold">{unread}</span>
                )}
              </button>
              {showNotifs && (
                <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-2xl border border-gray-100 z-50 overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                    <h3 className="text-xs font-bold text-gray-800">Notifications</h3>
                    {unread > 0 && (
                      <button onClick={markAllRead} className="text-[10px] text-purple-600 hover:text-purple-800 font-medium">
                        Mark all read
                      </button>
                    )}
                  </div>
                  <div className="max-h-72 overflow-y-auto divide-y divide-gray-50">
                    {notifs.length === 0 ? (
                      <p className="text-xs text-gray-400 text-center py-6">No notifications</p>
                    ) : (
                      notifs.slice(0, 10).map((n) => (
                        <button key={n.id} onClick={() => markNotifRead(n)}
                          className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors flex gap-3 items-start ${
                            !n.is_read ? "bg-purple-50/50" : ""
                          }`}>
                          <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${n.is_read ? "bg-gray-200" : "bg-purple-500"}`} />
                          <div className="flex-1 min-w-0">
                            <p className="text-[11px] font-semibold text-gray-800 truncate">{n.title}</p>
                            <p className="text-[10px] text-gray-500 line-clamp-2">{n.message}</p>
                            {n.created_at && (
                              <p className="text-[9px] text-gray-400 mt-0.5">{new Date(n.created_at).toLocaleString("en-IN")}</p>
                            )}
                          </div>
                          {n.link && <ExternalLink className="w-3 h-3 text-gray-300 mt-1 flex-shrink-0" />}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Welcome Banner */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-700 rounded-xl p-5 text-white">
          <h1 className="text-lg font-bold">Welcome, {data.lender.name}</h1>
          <p className="text-purple-200 text-xs mt-0.5">{data.lender.organization} · {data.lender.lender_type}</p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><Briefcase className="w-3.5 h-3.5" /> Investments</div>
            <p className="text-2xl font-bold">{data.portfolio.total_investments}</p>
            <p className="text-xs text-gray-400 mt-1">{data.portfolio.active_investments} active</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><Wallet className="w-3.5 h-3.5" /> Total Funded</div>
            <p className="text-2xl font-bold text-green-700">₹{data.portfolio.total_funded.toLocaleString("en-IN")}</p>
            <p className="text-xs text-gray-400 mt-1">₹{data.portfolio.total_returns.toLocaleString("en-IN")} returns</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><ArrowUpRight className="w-3.5 h-3.5" /> ROI</div>
            <p className="text-2xl font-bold text-blue-700">{data.portfolio.roi_percent.toFixed(1)}%</p>
            <p className="text-xs text-gray-400 mt-1">{data.portfolio.settled_investments} settled</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><Target className="w-3.5 h-3.5" /> Marketplace</div>
            <p className="text-2xl font-bold text-purple-700">{data.available_market.listings_count}</p>
            <p className="text-xs text-gray-400 mt-1">₹{data.available_market.total_value.toLocaleString("en-IN")} available</p>
          </div>
        </div>

        {/* Wallet & Withdraw Section */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <BanknoteIcon className="w-4 h-4 text-green-600" /> Wallet & Withdrawals
          </h2>
          <div className="grid sm:grid-cols-3 gap-4 mb-4">
            <div className="bg-green-50 rounded-xl p-4">
              <div className="flex items-center gap-2 text-green-700 text-[10px] uppercase tracking-wider font-semibold mb-1">
                <Unlock className="w-3 h-3" /> Available Balance
              </div>
              <p className="text-2xl font-bold text-green-800">₹{wallet.balance.toLocaleString("en-IN")}</p>
            </div>
            <div className="bg-amber-50 rounded-xl p-4">
              <div className="flex items-center gap-2 text-amber-700 text-[10px] uppercase tracking-wider font-semibold mb-1">
                <Lock className="w-3 h-3" /> Escrow Locked
              </div>
              <p className="text-2xl font-bold text-amber-800">₹{wallet.escrow_locked.toLocaleString("en-IN")}</p>
            </div>
            <div className="bg-blue-50 rounded-xl p-4">
              <div className="flex items-center gap-2 text-blue-700 text-[10px] uppercase tracking-wider font-semibold mb-1">
                <ArrowDownToLine className="w-3 h-3" /> Total Withdrawn
              </div>
              <p className="text-2xl font-bold text-blue-800">₹{wallet.total_withdrawn.toLocaleString("en-IN")}</p>
            </div>
          </div>

          {showWithdraw ? (
            <div className="flex items-center gap-3 bg-gray-50 rounded-xl p-4">
              <div className="flex-1">
                <label className="text-[10px] text-gray-500 uppercase tracking-wider font-medium block mb-1">Withdraw Amount (₹)</label>
                <input
                  type="number"
                  value={withdrawAmt}
                  onChange={(e) => setWithdrawAmt(e.target.value)}
                  placeholder={`Max ₹${wallet.balance.toLocaleString("en-IN")}`}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-200 focus:border-purple-500 outline-none"
                  max={wallet.balance}
                />
              </div>
              <button onClick={handleWithdraw} disabled={withdrawing || !withdrawAmt || parseFloat(withdrawAmt) <= 0}
                className="px-5 py-2.5 bg-green-600 text-white rounded-xl text-xs font-semibold hover:bg-green-700 disabled:opacity-50 transition-colors mt-5">
                {withdrawing ? <Loader2 className="w-4 h-4 animate-spin" /> : "Confirm Withdrawal"}
              </button>
              <button onClick={() => { setShowWithdraw(false); setWithdrawAmt(""); }}
                className="p-2 text-gray-400 hover:text-gray-600 mt-5">
                <X className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button onClick={() => setShowWithdraw(true)} disabled={wallet.balance <= 0}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl text-xs font-semibold hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 transition-all shadow-sm">
              <ArrowDownToLine className="w-4 h-4" /> Withdraw to Bank
            </button>
          )}
        </div>

        {/* Charts Row */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Monthly Trend */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-purple-500" /> Monthly Funding Trend
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data.monthly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(val) => `₹${Number(val).toLocaleString("en-IN")}`} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="funded" name="Funded" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="settled" name="Returns" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Risk Distribution */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-red-500" /> Risk Distribution
            </h2>
            {riskPie.filter(d => d.value > 0).length > 0 ? (
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie data={riskPie.filter(d => d.value > 0)} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                        paddingAngle={3} dataKey="value">
                        {riskPie.filter(d => d.value > 0).map((entry) => (
                          <Cell key={entry.name} fill={RISK_COLORS[entry.name] || "#6b7280"} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(val: number, name: string) => [`${val} investment${val !== 1 ? "s" : ""}`, name.charAt(0).toUpperCase() + name.slice(1) + " Risk"]} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex flex-col gap-2.5 min-w-[120px]">
                  {riskPie.map((entry) => {
                    const total = riskPie.reduce((s, e) => s + e.value, 0);
                    const pct = total > 0 ? Math.round((entry.value / total) * 100) : 0;
                    return (
                      <div key={entry.name} className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: RISK_COLORS[entry.name] || "#6b7280" }} />
                        <div>
                          <p className="text-xs font-medium text-gray-700 capitalize">{entry.name} Risk</p>
                          <p className="text-[11px] text-gray-400">{entry.value} ({pct}%)</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-gray-400 text-sm">No risk data</div>
            )}
          </div>
        </div>

        {/* Business Type + Upcoming Repayments */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Business Type Distribution */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Store className="w-4 h-4 text-blue-500" /> Business Type Distribution
            </h2>
            {bizPie.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={bizPie} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={100} />
                  <Tooltip />
                  <Bar dataKey="value" name="Listings" radius={[0, 4, 4, 0]}>
                    {bizPie.map((_, idx) => (
                      <Cell key={idx} fill={BIZ_COLORS[idx % BIZ_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-gray-400 text-sm">No business data</div>
            )}
          </div>

          {/* Upcoming Repayments */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-500" /> Upcoming Repayments
            </h2>
            {data.upcoming_repayments.length > 0 ? (
              <div className="space-y-2 max-h-[220px] overflow-y-auto">
                {data.upcoming_repayments.map((r) => (
                  <div key={`${r.listing_id}-${r.installment}`} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-xs font-medium text-gray-700">Listing #{r.listing_id} · Installment #{r.installment}</p>
                      <p className="text-[11px] text-gray-500">Due: {new Date(r.due_date).toLocaleDateString("en-IN")}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-gray-900">₹{r.amount.toLocaleString("en-IN")}</p>
                      <p className="text-[10px] font-medium text-amber-500">pending</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-gray-400 text-sm">No upcoming repayments</div>
            )}
          </div>
        </div>

        {/* Recent Activity — Compact */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-500" /> Recent Activity
          </h2>
          {data.recent_activity.length > 0 ? (
            <div className="space-y-1">
              {data.recent_activity.slice(0, 5).map((a) => (
                <div key={a.id} className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-gray-50 transition-colors">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
                  <span className="text-[11px] font-medium text-gray-700 flex-shrink-0 w-32 truncate">{a.action.replace(/_/g, " ")}</span>
                  <span className="text-[11px] text-gray-500 flex-1 truncate">{a.description}</span>
                  {a.created_at && (
                    <span className="text-[10px] text-gray-400 flex-shrink-0 whitespace-nowrap">{new Date(a.created_at).toLocaleDateString("en-IN")}</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">No recent activity</p>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid sm:grid-cols-3 gap-4">
          <Link href="/marketplace"
            className="bg-purple-600 text-white rounded-xl p-4 text-center hover:bg-purple-700 transition-colors">
            <Store className="w-6 h-6 mx-auto mb-1" />
            <p className="text-sm font-medium">Browse Marketplace</p>
          </Link>
          <Link href="/vendor/list"
            className="bg-blue-600 text-white rounded-xl p-4 text-center hover:bg-blue-700 transition-colors">
            <TrendingUp className="w-6 h-6 mx-auto mb-1" />
            <p className="text-sm font-medium">View Vendors</p>
          </Link>
          <Link href="/marketplace"
            className="bg-indigo-600 text-white rounded-xl p-4 text-center hover:bg-indigo-700 transition-colors">
            <Wallet className="w-6 h-6 mx-auto mb-1" />
            <p className="text-sm font-medium">My Investments</p>
          </Link>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
