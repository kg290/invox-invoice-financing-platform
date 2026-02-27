"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  FileText, Loader2, IndianRupee, TrendingUp, AlertCircle, Clock,
  Store, BarChart3, PieChart as PieIcon, Activity, Bell, Briefcase,
  ArrowUpRight, Wallet, Target, Shield,
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
  const lenderId = params.id as string;
  const [data, setData] = useState<LenderDashboardData | null>(null);
  const [notifs, setNotifs] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/dashboard/lender/${lenderId}`)
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));

    const storedUser = localStorage.getItem("invox_user");
    if (storedUser) {
      const user = JSON.parse(storedUser);
      api.get(`/notifications/${user.id}`).then((r) => setNotifs(r.data)).catch(() => {});
      api.get(`/notifications/${user.id}/unread-count`).then((r) => setUnread(r.data.unread)).catch(() => {});
    }
  }, [lenderId]);

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
            <Link href="/marketplace" className="text-xs text-gray-500 hover:text-gray-700">Marketplace</Link>
            <div className="relative">
              <Bell className="w-5 h-5 text-gray-400" />
              {unread > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full text-[10px] flex items-center justify-center font-bold">{unread}</span>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Welcome Banner */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-700 rounded-2xl p-6 text-white">
          <h1 className="text-xl font-bold">Welcome, {data.lender.name}</h1>
          <p className="text-purple-200 text-sm mt-1">{data.lender.organization} · {data.lender.lender_type}</p>
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

        {/* Charts Row */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Monthly Trend */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-purple-500" /> Monthly Funding Trend
            </h2>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={data.monthly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(val) => `₹${Number(val).toLocaleString("en-IN")}`} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="funded" name="Funded" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="returns" name="Returns" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Risk Distribution */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-red-500" /> Risk Distribution
            </h2>
            {riskPie.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={riskPie} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                    paddingAngle={3} dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}>
                    {riskPie.map((entry) => (
                      <Cell key={entry.name} fill={RISK_COLORS[entry.name] || "#6b7280"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[250px] text-gray-400 text-sm">No risk data</div>
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
              <ResponsiveContainer width="100%" height={250}>
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
              <div className="flex items-center justify-center h-[250px] text-gray-400 text-sm">No business data</div>
            )}
          </div>

          {/* Upcoming Repayments */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-500" /> Upcoming Repayments
            </h2>
            {data.upcoming_repayments.length > 0 ? (
              <div className="space-y-2 max-h-[250px] overflow-y-auto">
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
              <div className="flex items-center justify-center h-[250px] text-gray-400 text-sm">No upcoming repayments</div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-500" /> Recent Activity
          </h2>
          {data.recent_activity.length > 0 ? (
            <div className="grid sm:grid-cols-2 gap-3">
              {data.recent_activity.map((a) => (
                <div key={a.id} className="flex gap-3 items-start p-3 bg-gray-50 rounded-lg">
                  <div className="w-2 h-2 rounded-full bg-indigo-400 mt-1.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-medium text-gray-700">{a.action}</p>
                    <p className="text-[11px] text-gray-500">{a.description}</p>
                    {a.created_at && (
                      <p className="text-[10px] text-gray-400 mt-0.5">{new Date(a.created_at).toLocaleString("en-IN")}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">No recent activity</p>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid sm:grid-cols-3 gap-4">
          <Link href="/marketplace"
            className="bg-purple-600 text-white rounded-xl p-4 text-center hover:bg-purple-700 transition-colors">
            <Store className="w-6 h-6 mx-auto mb-1" />
            <p className="text-sm font-medium">Browse Marketplace</p>
          </Link>
          <Link href="/kyc"
            className="bg-amber-600 text-white rounded-xl p-4 text-center hover:bg-amber-700 transition-colors">
            <Shield className="w-6 h-6 mx-auto mb-1" />
            <p className="text-sm font-medium">KYC Verification</p>
          </Link>
          <Link href="/vendors"
            className="bg-blue-600 text-white rounded-xl p-4 text-center hover:bg-blue-700 transition-colors">
            <TrendingUp className="w-6 h-6 mx-auto mb-1" />
            <p className="text-sm font-medium">View Vendors</p>
          </Link>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
