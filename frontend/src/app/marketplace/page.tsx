"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, Store, Loader2, IndianRupee, ShieldCheck, Calendar,
  TrendingUp, Filter, CheckCircle, AlertTriangle, Building2, Clock,
  Percent, UserPlus, Search, MapPin, Users, Star, ArrowUpRight,
  Briefcase, ChevronDown, X, Sparkles, BadgeCheck, BarChart3,
  CircleDollarSign, Shield, Eye,
} from "lucide-react";
import api, { getErrorMessage, fileUrl } from "@/lib/api";
import { MarketplaceBrowseItem, LenderResponse } from "@/lib/types";

/* ── helpers ── */
const statusConfig: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  open: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", label: "Open for Funding" },
  partially_funded: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", label: "Funding In Progress" },
  funded: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500", label: "Fully Funded" },
  settled: { bg: "bg-gray-100", text: "text-gray-600", dot: "bg-gray-400", label: "Settled" },
  defaulted: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", label: "Defaulted" },
};



const cibilGrade = (score: number | null) => {
  if (!score) return { grade: "N/A", color: "text-gray-400", bg: "bg-gray-100" };
  if (score >= 750) return { grade: "Excellent", color: "text-emerald-700", bg: "bg-emerald-50" };
  if (score >= 700) return { grade: "Good", color: "text-green-700", bg: "bg-green-50" };
  if (score >= 650) return { grade: "Fair", color: "text-yellow-700", bg: "bg-yellow-50" };
  return { grade: "Poor", color: "text-red-700", bg: "bg-red-50" };
};

const timeAgo = (dateStr: string | null) => {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return `${Math.floor(days / 30)}mo ago`;
};

const categoryIcons: Record<string, string> = {
  "Textiles & Handloom": "🧵", "Food Processing": "�", "Leather & Footwear": "👜",
  "Auto Components Manufacturing": "⚙️", "Garment & Knitwear Export": "👕",
  "IT & Software Services": "💻", "Pharmaceutical Manufacturing": "💊",
  "Steel & Metal Fabrication": "🔩", "Ceramics & Pottery": "🏺",
  "Electronics Manufacturing": "🔌", Manufacturing: "🏭", Trading: "📦",
  Services: "💼", Retail: "🛒", Construction: "🏗️",
  "Tiffin & Catering": "🍱", "Street Food": "🍲", "Grocery & Kirana": "🏪",
  "Tailoring & Alteration": "✂️", "Salon & Beauty": "💇", "Laundry": "👔",
  "Printing & Stationery": "🖨️", "Auto Repair": "🔧", "Dairy & Milk": "🥛",
};

const gradientBgs = [
  "from-violet-500 to-purple-600",
  "from-blue-500 to-indigo-600",
  "from-emerald-500 to-teal-600",
  "from-orange-500 to-red-500",
  "from-pink-500 to-rose-600",
  "from-cyan-500 to-blue-600",
  "from-amber-500 to-orange-600",
  "from-fuchsia-500 to-purple-600",
];

export default function MarketplacePage() {
  const [listings, setListings] = useState<MarketplaceBrowseItem[]>([]);
  const [lenders, setLenders] = useState<LenderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState("");
  const [chainValid, setChainValid] = useState<boolean | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [advFilters, setAdvFilters] = useState({
    amount_min: "", amount_max: "", interest_min: "", interest_max: "",
    business_type: "", sort_by: "created_at", sort_order: "desc",
  });

  // Lender registration modal
  const [showLenderModal, setShowLenderModal] = useState(false);
  const [lenderForm, setLenderForm] = useState({ name: "", email: "", phone: "", organization: "", lender_type: "individual" });
  const [registering, setRegistering] = useState(false);

  const buildUrl = () => {
    const params = new URLSearchParams();
    if (filter) params.set("status", filter);
    if (advFilters.amount_min) params.set("amount_min", advFilters.amount_min);
    if (advFilters.amount_max) params.set("amount_max", advFilters.amount_max);
    if (advFilters.interest_min) params.set("interest_min", advFilters.interest_min);
    if (advFilters.interest_max) params.set("interest_max", advFilters.interest_max);
    if (advFilters.business_type) params.set("business_type", advFilters.business_type);
    if (advFilters.sort_by) params.set("sort_by", advFilters.sort_by);
    if (advFilters.sort_order) params.set("sort_order", advFilters.sort_order);
    const qs = params.toString();
    return `/marketplace/listings${qs ? `?${qs}` : ""}`;
  };

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      api.get(buildUrl()),
      api.get("/marketplace/lenders"),
    ]).then(([listRes, lenderRes]) => {
      setListings(listRes.data);
      setLenders(lenderRes.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };
  useEffect(fetchData, [filter]);

  // Client-side search filtering
  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return listings;
    const q = searchQuery.toLowerCase();
    return listings.filter((l) =>
      l.business_name.toLowerCase().includes(q) ||
      l.vendor_name.toLowerCase().includes(q) ||
      (l.business_category || "").toLowerCase().includes(q) ||
      (l.business_type || "").toLowerCase().includes(q) ||
      (l.invoice_number || "").toLowerCase().includes(q) ||
      (l.business_city || "").toLowerCase().includes(q)
    );
  }, [listings, searchQuery]);

  const registerLender = async () => {
    if (!lenderForm.name || !lenderForm.email) { toast.error("Name and email are required"); return; }
    setRegistering(true);
    try {
      await api.post("/marketplace/lender", lenderForm);
      toast.success("Lender registered successfully!");
      setShowLenderModal(false);
      setLenderForm({ name: "", email: "", phone: "", organization: "", lender_type: "individual" });
      fetchData();
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Registration failed"));
    }
    setRegistering(false);
  };

  const validateChain = async () => {
    try {
      const r = await api.get("/marketplace/blockchain/validate");
      setChainValid(r.data.valid);
      toast.success(r.data.valid ? "Blockchain is valid ✓" : "Blockchain integrity compromised!");
    } catch {
      toast.error("Validation failed");
    }
  };

  const openCount = listings.filter((l) => l.listing_status === "open" || l.listing_status === "partially_funded").length;
  const totalValue = listings.reduce((s, l) => s + l.requested_amount, 0);
  const avgInterest = listings.length > 0 ? (listings.reduce((s, l) => s + l.max_interest_rate, 0) / listings.length).toFixed(1) : "0";

  const inputCls = "w-full px-3 py-2 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all bg-white";

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-[#f8f9fc]">
      {/* ─── Sticky Navigation ─── */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900 tracking-tight">Invo<span className="text-indigo-600">X</span></span>
          </Link>

          <div className="flex items-center gap-2">
            <button onClick={validateChain}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 text-indigo-600 hover:bg-indigo-50 rounded-xl text-xs font-medium transition-all">
              <ShieldCheck className="w-3.5 h-3.5" />
              {chainValid === true ? "Chain Valid ✓" : chainValid === false ? "Chain Invalid!" : "Verify Chain"}
            </button>
            <button onClick={() => setShowLenderModal(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-xl text-xs font-semibold hover:shadow-lg hover:shadow-indigo-200 transition-all active:scale-[0.98]">
              <UserPlus className="w-3.5 h-3.5" /> Become a Lender
            </button>
          </div>
        </div>
      </header>

      {/* ─── Hero Section ─── */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700" />
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }} />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-8">
          <div className="flex items-start justify-between">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/15 backdrop-blur-sm rounded-full text-white/90 text-xs font-medium mb-4">
                <Sparkles className="w-3.5 h-3.5" /> Blockchain-Secured Invoice Marketplace
              </div>
              <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3 tracking-tight">
                MSME Invoice<br />Marketplace
              </h1>
              <p className="text-indigo-100 max-w-lg text-sm leading-relaxed">
                Fund India&apos;s Micro, Small & Medium Enterprises. Udyam-verified invoices, AI credit scoring, and blockchain-secured transparency for every MSME transaction.
              </p>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
            {[
              { label: "Total Listings", value: listings.length, icon: Store, accent: "from-white/20 to-white/5" },
              { label: "Open to Fund", value: openCount, icon: CircleDollarSign, accent: "from-emerald-400/30 to-emerald-400/5" },
              { label: "Total Value", value: `₹${(totalValue / 100000).toFixed(1)}L`, icon: TrendingUp, accent: "from-amber-400/30 to-amber-400/5" },
              { label: "Avg Interest", value: `${avgInterest}%`, icon: BarChart3, accent: "from-cyan-400/30 to-cyan-400/5" },
            ].map((stat) => (
              <div key={stat.label} className={`bg-gradient-to-br ${stat.accent} backdrop-blur-sm rounded-2xl p-4 border border-white/10`}>
                <div className="flex items-center gap-2 mb-1">
                  <stat.icon className="w-4 h-4 text-white/70" />
                  <span className="text-white/70 text-[11px] font-medium uppercase tracking-wider">{stat.label}</span>
                </div>
                <p className="text-2xl font-bold text-white">{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Search bar */}
          <div className="mt-4 relative max-w-2xl">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by business name, category, city, or invoice..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3.5 bg-white rounded-2xl text-sm text-gray-900 placeholder:text-gray-400 shadow-xl shadow-black/10 focus:ring-2 focus:ring-indigo-300 outline-none"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-4">
        {/* ─── Filter Bar ─── */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 mb-4">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            {/* Status pills */}
            <div className="flex items-center gap-2 flex-wrap">
              {[
                { key: "", label: "All", count: listings.length },
                { key: "open", label: "Open", count: listings.filter(l => l.listing_status === "open").length },
                { key: "partially_funded", label: "In Progress", count: listings.filter(l => l.listing_status === "partially_funded").length },
                { key: "funded", label: "Funded", count: listings.filter(l => l.listing_status === "funded").length },
                { key: "settled", label: "Settled", count: listings.filter(l => l.listing_status === "settled").length },
              ].map((f) => (
                <button key={f.key} onClick={() => setFilter(f.key)}
                  className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                    filter === f.key
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-200"
                      : "bg-gray-50 text-gray-600 hover:bg-gray-100"
                  }`}>
                  {f.label}
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-md ${filter === f.key ? "bg-white/20" : "bg-gray-200/60"}`}>{f.count}</span>
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              {/* Sort */}
              <select
                value={advFilters.sort_by}
                onChange={(e) => { setAdvFilters({ ...advFilters, sort_by: e.target.value }); setTimeout(fetchData, 0); }}
                className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium text-gray-900 outline-none cursor-pointer hover:bg-gray-100 transition-colors"
              >
                <option value="created_at">Newest First</option>
                <option value="amount">Amount</option>
                <option value="interest">Interest Rate</option>
              </select>

              {/* Advanced filter toggle */}
              <button onClick={() => setShowFilters(!showFilters)}
                className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-all border ${
                  showFilters ? "bg-indigo-50 border-indigo-200 text-indigo-700" : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
                }`}>
                <Filter className="w-3.5 h-3.5" /> Filters
                <ChevronDown className={`w-3 h-3 transition-transform ${showFilters ? "rotate-180" : ""}`} />
              </button>

              {/* View toggle */}
              <div className="hidden sm:flex bg-gray-100 rounded-xl p-0.5">
                <button onClick={() => setViewMode("grid")} className={`p-1.5 rounded-lg transition-all ${viewMode === "grid" ? "bg-white shadow-sm" : ""}`}>
                  <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
                </button>
                <button onClick={() => setViewMode("list")} className={`p-1.5 rounded-lg transition-all ${viewMode === "list" ? "bg-white shadow-sm" : ""}`}>
                  <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
                </button>
              </div>
            </div>
          </div>

          {/* Advanced filters panel */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-100 grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 mb-1.5 uppercase tracking-wider">Amount Range (₹)</label>
                <div className="flex gap-1.5">
                  <input type="number" placeholder="Min" value={advFilters.amount_min}
                    onChange={(e) => setAdvFilters({ ...advFilters, amount_min: e.target.value })}
                    className="w-1/2 px-2.5 py-2 border border-gray-200 rounded-xl text-xs text-gray-900 placeholder:text-gray-400 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all" />
                  <input type="number" placeholder="Max" value={advFilters.amount_max}
                    onChange={(e) => setAdvFilters({ ...advFilters, amount_max: e.target.value })}
                    className="w-1/2 px-2.5 py-2 border border-gray-200 rounded-xl text-xs text-gray-900 placeholder:text-gray-400 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all" />
                </div>
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 mb-1.5 uppercase tracking-wider">Interest Rate (%)</label>
                <div className="flex gap-1.5">
                  <input type="number" placeholder="Min" value={advFilters.interest_min}
                    onChange={(e) => setAdvFilters({ ...advFilters, interest_min: e.target.value })}
                    className="w-1/2 px-2.5 py-2 border border-gray-200 rounded-xl text-xs text-gray-900 placeholder:text-gray-400 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all" />
                  <input type="number" placeholder="Max" value={advFilters.interest_max}
                    onChange={(e) => setAdvFilters({ ...advFilters, interest_max: e.target.value })}
                    className="w-1/2 px-2.5 py-2 border border-gray-200 rounded-xl text-xs text-gray-900 placeholder:text-gray-400 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all" />
                </div>
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 mb-1.5 uppercase tracking-wider">Business Type</label>
                <select value={advFilters.business_type}
                  onChange={(e) => setAdvFilters({ ...advFilters, business_type: e.target.value })}
                  className="w-full px-2.5 py-2 border border-gray-200 rounded-xl text-xs text-gray-900 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all cursor-pointer">
                  <option value="">All Types</option>
                  {["Proprietorship", "Partnership", "LLP", "Pvt Ltd"].map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="sm:col-span-2 lg:col-span-4 flex items-center gap-2 pt-1">
                <button onClick={fetchData}
                  className="px-5 py-2 bg-indigo-600 text-white rounded-xl text-xs font-semibold hover:bg-indigo-700 transition-colors shadow-sm">
                  Apply Filters
                </button>
                <button onClick={() => {
                  setAdvFilters({ amount_min: "", amount_max: "", interest_min: "", interest_max: "", business_type: "", sort_by: "created_at", sort_order: "desc" });
                  setFilter("");
                }}
                  className="px-5 py-2 border border-gray-200 rounded-xl text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors">
                  Reset All
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ─── Results Count ─── */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-500">
            Showing <span className="font-semibold text-gray-900">{filtered.length}</span> listing{filtered.length !== 1 ? "s" : ""}
            {searchQuery && <span className="text-indigo-600"> for &quot;{searchQuery}&quot;</span>}
          </p>
          <p className="text-xs text-gray-400">{lenders.length} registered lender{lenders.length !== 1 ? "s" : ""}</p>
        </div>

        {/* ─── Listings Grid ─── */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-10">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-indigo-100 rounded-full" />
              <div className="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin absolute inset-0" />
            </div>
            <p className="text-sm text-gray-500 mt-4">Loading marketplace...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-10 bg-white rounded-2xl border border-gray-100">
            <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Store className="w-8 h-8 text-gray-300" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">No listings found</h3>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              {searchQuery ? "Try adjusting your search or filters" : "There are currently no listings matching your criteria"}
            </p>
          </div>
        ) : (
          <div className={viewMode === "grid" ? "grid sm:grid-cols-2 lg:grid-cols-3 gap-4" : "space-y-3"}>
            {filtered.map((l, idx) => {
              const cibil = cibilGrade(l.cibil_score);
              const st = statusConfig[l.listing_status] || statusConfig.open;
              const gradientIdx = idx % gradientBgs.length;
              const catIcon = categoryIcons[l.business_category || ""] || "🏢";
              const yearsInBiz = l.year_of_establishment ? new Date().getFullYear() - l.year_of_establishment : null;

              if (viewMode === "list") {
                return (
                  <Link key={l.id} href={`/marketplace/${l.id}`}
                    className="group bg-white rounded-2xl border border-gray-100 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-50 transition-all duration-300 flex overflow-hidden">
                    {/* Left accent */}
                    <div className={`w-2 bg-gradient-to-b ${gradientBgs[gradientIdx]} flex-shrink-0`} />
                    <div className="flex-1 p-5 flex items-center gap-6">
                      <div className="flex-shrink-0">
                        {l.business_images?.length > 0 ? (
                          <img src={fileUrl(l.business_images[0])} alt={l.business_name} className="w-16 h-16 rounded-xl object-cover" />
                        ) : (
                          <div className={`w-16 h-16 bg-gradient-to-br ${gradientBgs[gradientIdx]} rounded-xl flex items-center justify-center`}>
                            <span className="text-2xl">{catIcon}</span>
                          </div>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-sm font-bold text-gray-900 truncate">{l.business_name}</h3>
                          {l.profile_status === "verified" && <BadgeCheck className="w-4 h-4 text-indigo-500 flex-shrink-0" />}
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${st.bg} ${st.text}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} /> {st.label}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500">{l.business_category} · {l.business_type} · {l.business_city}, {l.business_state}</p>
                        {l.listing_title && <p className="text-xs text-indigo-600 font-medium mt-0.5 truncate">{l.listing_title}</p>}
                      </div>
                      <div className="hidden md:flex items-center gap-8 flex-shrink-0">
                        <div className="text-center">
                          <p className="text-lg font-bold text-gray-900">₹{(l.requested_amount / 1000).toFixed(0)}K</p>
                          <p className="text-[10px] text-gray-400 uppercase">Amount</p>
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-bold text-green-600">{l.max_interest_rate}%</p>
                          <p className="text-[10px] text-gray-400 uppercase">Interest</p>
                        </div>
                        {yearsInBiz !== null && (
                          <div className="text-center">
                            <p className="text-sm font-bold text-gray-700">{yearsInBiz}yr{yearsInBiz > 1 ? "s" : ""}</p>
                            <p className="text-[10px] text-gray-400 uppercase">In Business</p>
                          </div>
                        )}
                        <ArrowUpRight className="w-5 h-5 text-gray-300 group-hover:text-indigo-500 transition-colors" />
                      </div>
                    </div>
                  </Link>
                );
              }

              return (
                <Link key={l.id} href={`/marketplace/${l.id}`}
                  className="group bg-white rounded-2xl border border-gray-100 hover:border-indigo-200 hover:shadow-xl hover:shadow-indigo-50 transition-all duration-300 flex flex-col overflow-hidden">
                  
                  {/* Card Header / Image Section */}
                  <div className="relative">
                    {l.business_images?.length > 0 ? (
                          <img src={fileUrl(l.business_images[0])} alt={l.business_name} className="w-full h-32 object-cover" />
                    ) : (
                      <div className={`w-full h-32 bg-gradient-to-br ${gradientBgs[gradientIdx]} flex items-center justify-center relative overflow-hidden`}>
                        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23fff' fill-opacity='0.15'%3E%3Cpath d='M0 40L40 0H20L0 20M40 40V20L20 40'/%3E%3C/g%3E%3C/svg%3E\")" }} />
                        <div className="text-center relative z-10">
                          <span className="text-4xl mb-2 block">{catIcon}</span>
                          <p className="text-white/80 text-xs font-medium">{l.business_category || "Business"}</p>
                        </div>
                      </div>
                    )}

                    {/* Status badge on image */}
                    <div className="absolute top-3 left-3">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold backdrop-blur-md ${st.bg} ${st.text} shadow-sm`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${st.dot} animate-pulse`} /> {st.label}
                      </span>
                    </div>

                    {/* Blockchain verified badge */}
                    {l.blockchain_hash && (
                      <div className="absolute top-3 right-3">
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium bg-white/90 backdrop-blur-md text-indigo-700 shadow-sm">
                          <Shield className="w-3 h-3" /> Secured
                        </span>
                      </div>
                    )}

                    {/* Time badge */}
                    {l.created_at && (
                      <div className="absolute bottom-3 right-3">
                        <span className="text-[10px] font-medium text-white/90 bg-black/40 backdrop-blur-sm px-2 py-0.5 rounded-md">
                          {timeAgo(l.created_at)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Card Body */}
                  <div className="p-4 flex-1 flex flex-col">
                    {/* Business name & info */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <h3 className="text-base font-bold text-gray-900 truncate group-hover:text-indigo-700 transition-colors">{l.business_name}</h3>
                          {l.profile_status === "verified" && (
                            <BadgeCheck className="w-4 h-4 text-indigo-500 flex-shrink-0" />
                          )}
                        </div>
                        <p className="text-xs text-gray-500 flex items-center gap-1.5">
                          <span>{l.vendor_name}</span>
                          {l.business_city && (
                            <>
                              <span className="text-gray-300">·</span>
                              <MapPin className="w-3 h-3 text-gray-400" />
                              <span>{l.business_city}</span>
                            </>
                          )}
                        </p>
                      </div>
                    </div>

                    {/* Business category tag */}
                    {l.business_category && (
                      <div className="flex items-center gap-1.5 mb-3">
                        <span className="text-[10px] font-medium bg-gray-100 text-gray-600 px-2 py-0.5 rounded-md">{catIcon} {l.business_category}</span>
                        {l.business_type && (
                          <span className="text-[10px] font-medium bg-gray-100 text-gray-600 px-2 py-0.5 rounded-md">{l.business_type}</span>
                        )}
                      </div>
                    )}

                    {/* Description snippet */}
                    {l.listing_title && (
                      <p className="text-sm font-semibold text-indigo-700 mb-1">{l.listing_title}</p>
                    )}
                    {(l.listing_description || l.business_description) && (
                      <p className="text-xs text-gray-500 mb-3 line-clamp-2 leading-relaxed">{l.listing_description || l.business_description}</p>
                    )}

                    {/* Financial metrics */}
                    <div className="bg-gray-50 rounded-xl p-2.5 space-y-1.5 mb-3">
                      <div className="flex justify-between items-center">
                        <span className="text-[11px] text-gray-500 flex items-center gap-1"><IndianRupee className="w-3 h-3" /> Funding Ask</span>
                        <span className="text-sm font-bold text-gray-900">₹{l.requested_amount.toLocaleString("en-IN")}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[11px] text-gray-500 flex items-center gap-1"><Percent className="w-3 h-3" /> Returns</span>
                        <span className="text-sm font-bold text-emerald-600">{l.max_interest_rate}% <span className="font-normal text-gray-400 text-[10px]">p.a.</span></span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[11px] text-gray-500 flex items-center gap-1"><Clock className="w-3 h-3" /> Tenure</span>
                        <span className="text-xs font-semibold text-gray-700">{l.repayment_period_days} days</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-[11px] text-gray-500 flex items-center gap-1"><FileText className="w-3 h-3" /> Invoice</span>
                        <span className="text-xs font-medium text-gray-600">₹{(l.grand_total ?? 0).toLocaleString("en-IN")}</span>
                      </div>
                    </div>

                    {/* Business Info Tags */}
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {l.profile_status === "verified" && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-medium bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-md">
                          <BadgeCheck className="w-3 h-3" /> Udyam Verified
                        </span>
                      )}
                      {yearsInBiz !== null && (
                        <span className="text-[10px] font-medium bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md">
                          {yearsInBiz}+ yr{yearsInBiz > 1 ? "s" : ""} in business
                        </span>
                      )}
                      {l.cibil_score && (
                        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-md ${cibil.bg} ${cibil.color}`}>
                          CIBIL: {l.cibil_score} ({cibil.grade})
                        </span>
                      )}
                    </div>

                    {/* ── Community Pot Progress Bar ── */}
                    {(l.listing_status === "open" || l.listing_status === "partially_funded" || l.listing_status === "funded") && (
                      <div className="mb-3 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-2.5 border border-indigo-100">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[11px] font-semibold text-indigo-700 flex items-center gap-1">
                            <Users className="w-3 h-3" /> Community Pot
                          </span>
                          <span className="text-[11px] font-bold text-indigo-700">
                            {l.funding_progress_pct.toFixed(0)}% Funded
                            {l.total_investors > 0 && <span className="font-normal text-indigo-400 ml-1">by {l.total_investors} investor{l.total_investors > 1 ? "s" : ""}</span>}
                          </span>
                        </div>
                        <div className="w-full h-2.5 bg-white rounded-full overflow-hidden shadow-inner">
                          <div
                            className={`h-full rounded-full transition-all duration-1000 ease-out ${
                              l.funding_progress_pct >= 100
                                ? "bg-gradient-to-r from-emerald-400 to-green-500"
                                : l.funding_progress_pct >= 50
                                ? "bg-gradient-to-r from-indigo-400 to-purple-500"
                                : "bg-gradient-to-r from-blue-400 to-indigo-500"
                            }`}
                            style={{ width: `${Math.min(100, l.funding_progress_pct)}%` }}
                          />
                        </div>
                        <div className="flex justify-between mt-1.5">
                          <span className="text-[10px] text-indigo-500">₹{(l.total_funded_amount || 0).toLocaleString("en-IN")} raised</span>
                          <span className="text-[10px] text-indigo-500">
                            {l.remaining_amount > 0 ? `₹${l.remaining_amount.toLocaleString("en-IN")} left` : "Fully Funded ✓"}
                          </span>
                        </div>
                        {l.listing_status !== "funded" && l.min_investment > 0 && (
                          <p className="text-[9px] text-indigo-400 mt-1 text-center">Min. investment: ₹{l.min_investment.toLocaleString("en-IN")}</p>
                        )}
                      </div>
                    )}

                    {/* Bottom Row: Reviews + Deals + CTA */}
                    <div className="mt-auto pt-3 border-t border-gray-100 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {/* Rating */}
                        <div className="flex items-center gap-1">
                          <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                          <span className="text-xs font-bold text-gray-700">{(l.average_rating || 0).toFixed(1)}</span>
                          <span className="text-[10px] text-gray-400">({l.total_reviews || 0})</span>
                        </div>
                        {/* Funded deals */}
                        {l.total_funded_deals > 0 && (
                          <span className="text-[10px] font-medium text-gray-500 flex items-center gap-0.5">
                            <CheckCircle className="w-3 h-3 text-emerald-500" /> {l.total_funded_deals} deal{l.total_funded_deals > 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 group-hover:text-indigo-700 transition-colors">
                        <Eye className="w-3.5 h-3.5" /> View Details
                        <ArrowUpRight className="w-3 h-3 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {/* ─── Lender Registration Modal ─── */}
      {showLenderModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowLenderModal(false)}>
          <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl transform transition-all" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Become a Lender</h2>
                <p className="text-xs text-gray-500 mt-1">Start funding invoices and earn returns</p>
              </div>
              <button onClick={() => setShowLenderModal(false)} className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Full Name *</label>
                <input value={lenderForm.name} onChange={(e) => setLenderForm({ ...lenderForm, name: e.target.value })} className={inputCls} placeholder="Enter your full name" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Email *</label>
                <input type="email" value={lenderForm.email} onChange={(e) => setLenderForm({ ...lenderForm, email: e.target.value })} className={inputCls} placeholder="email@example.com" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Phone</label>
                  <input value={lenderForm.phone} onChange={(e) => setLenderForm({ ...lenderForm, phone: e.target.value })} className={inputCls} placeholder="+91..." />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1.5">Type</label>
                  <select value={lenderForm.lender_type} onChange={(e) => setLenderForm({ ...lenderForm, lender_type: e.target.value })}
                    className={inputCls + " cursor-pointer"}>
                    <option value="individual">Individual</option>
                    <option value="nbfc">NBFC</option>
                    <option value="bank">Bank</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Organization</label>
                <input value={lenderForm.organization} onChange={(e) => setLenderForm({ ...lenderForm, organization: e.target.value })} className={inputCls} placeholder="Company or NBFC name (optional)" />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowLenderModal(false)}
                className="flex-1 px-4 py-3 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors">
                Cancel
              </button>
              <button onClick={registerLender} disabled={registering}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-xl text-sm font-semibold hover:shadow-lg hover:shadow-indigo-200 disabled:opacity-60 inline-flex items-center justify-center gap-2 transition-all active:scale-[0.98]">
                {registering ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                Register
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer spacing */}
      <div className="h-6" />
    </div>
    </ProtectedRoute>
  );
}
