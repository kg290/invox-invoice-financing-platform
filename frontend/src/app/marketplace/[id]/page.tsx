"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, ArrowLeft, Loader2, ShieldCheck, AlertCircle, IndianRupee,
  Building2, Calendar, Percent, Clock, TrendingUp, Download,
  FileBarChart2, HandCoins, CheckCircle, Star, Briefcase, Globe,
  Activity, CreditCard, MapPin, Users, BadgeCheck, Shield, ChevronLeft,
  ChevronRight, ArrowUpRight, AlertTriangle, CircleDollarSign, Gauge,
  Eye, Lock, BarChart3, X, ExternalLink, Info, Bot, Zap,
  MessageSquare,
} from "lucide-react";
import api, { getErrorMessage, fileUrl } from "@/lib/api";
import { MarketplaceDetailItem, LenderResponse, RepaymentInstallment, ActivityItem, NegotiationChat, NegotiationChatMessage } from "@/lib/types";
import { createFundingOrder, createRepaymentOrder, createPayAllOrder, requestRefund } from "@/lib/razorpay";
import InvoXPayCheckout, { OrderData } from "@/components/InvoXPayCheckout";
import { useAuth } from "@/lib/auth";

/* ── helpers ── */
const statusConfig: Record<string, { bg: string; text: string; dot: string; label: string; border: string }> = {
  open: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", label: "Open for Funding", border: "border-emerald-200" },
  partially_funded: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", label: "Funding In Progress", border: "border-amber-200" },
  funded: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-500", label: "Fully Funded", border: "border-blue-200" },
  settled: { bg: "bg-gray-100", text: "text-gray-600", dot: "bg-gray-400", label: "Settled", border: "border-gray-200" },
  defaulted: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", label: "Defaulted", border: "border-red-200" },
};

const riskMeter = (score: number | null) => {
  const s = score ?? 50;
  if (s <= 25) return { label: "Very Low", color: "text-emerald-600", bg: "bg-emerald-500", fill: "from-emerald-400 to-emerald-600" };
  if (s <= 40) return { label: "Low", color: "text-green-600", bg: "bg-green-500", fill: "from-green-400 to-green-600" };
  if (s <= 55) return { label: "Moderate", color: "text-yellow-600", bg: "bg-yellow-500", fill: "from-yellow-400 to-yellow-600" };
  if (s <= 70) return { label: "High", color: "text-orange-600", bg: "bg-orange-500", fill: "from-orange-400 to-orange-600" };
  return { label: "Very High", color: "text-red-600", bg: "bg-red-500", fill: "from-red-400 to-red-600" };
};

const cibilGrade = (score: number | null) => {
  if (!score) return { grade: "N/A", color: "text-gray-400", bg: "bg-gray-50", ring: "ring-gray-200" };
  if (score >= 750) return { grade: "Excellent", color: "text-emerald-700", bg: "bg-emerald-50", ring: "ring-emerald-200" };
  if (score >= 700) return { grade: "Good", color: "text-green-700", bg: "bg-green-50", ring: "ring-green-200" };
  if (score >= 650) return { grade: "Fair", color: "text-yellow-700", bg: "bg-yellow-50", ring: "ring-yellow-200" };
  return { grade: "Poor", color: "text-red-700", bg: "bg-red-50", ring: "ring-red-200" };
};

const gradientBgs = [
  "from-violet-500 to-purple-600", "from-blue-500 to-indigo-600",
  "from-emerald-500 to-teal-600", "from-orange-500 to-red-500",
];

const categoryIcons: Record<string, string> = {
  Manufacturing: "🏭", Trading: "📦", Services: "💼", Retail: "🛒",
  "Agriculture & Allied": "🌾", Construction: "🏗️", Textiles: "🧵",
  "Food Processing": "🍕", "IT & Software": "💻", Healthcare: "🏥",
};

export default function MarketplaceDetailPage() {
  const params = useParams();
  const listingId = params.id as string;
  const { user } = useAuth();
  const isLender = user?.role === "lender";

  const [detail, setDetail] = useState<MarketplaceDetailItem | null>(null);
  const [lenders, setLenders] = useState<LenderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [contractLoading, setContractLoading] = useState(false);
  const [gstLoading, setGstLoading] = useState(false);
  const [gstData, setGstData] = useState<Record<string, unknown> | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "financials" | "invoice" | "activity">("overview");
  const [imageIdx, setImageIdx] = useState(0);

  // Funding form
  const [showFund, setShowFund] = useState(false);
  const [fundForm, setFundForm] = useState({ lender_id: 0, funded_amount: 0, offered_interest_rate: 0 });
  const [funding, setFunding] = useState(false);

  // Repayment & Activity
  const [repayments, setRepayments] = useState<RepaymentInstallment[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [payingId, setPayingId] = useState<number | null>(null);

  // InvoX Pay checkout
  const [checkoutOrder, setCheckoutOrder] = useState<OrderData | null>(null);
  const [checkoutContext, setCheckoutContext] = useState<{ type: "funding" | "repayment" | "repayment_all"; installment_number?: number }>({ type: "funding" });

  // Refund
  const [showRefund, setShowRefund] = useState(false);
  const [refundReason, setRefundReason] = useState("Lender requested refund");
  const [refunding, setRefunding] = useState(false);

  // Pay all
  const [payingAll, setPayingAll] = useState(false);

  // AI Negotiator Chat
  const [chatSession, setChatSession] = useState<NegotiationChat | null>(null);
  const [showChat, setShowChat] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [offerForm, setOfferForm] = useState({ rate: 0, amount: 0, message: "" });
  const [sendingOffer, setSendingOffer] = useState(false);
  const [listingNegotiations, setListingNegotiations] = useState<NegotiationChat[]>([]);

  const fetchRepayments = () => {
    api.get(`/marketplace/listings/${listingId}/repayment`).then((r) => setRepayments(r.data.installments || [])).catch(() => {});
  };
  const fetchActivity = () => {
    api.get(`/activity/listing/${listingId}`).then((r) => setActivities(r.data)).catch(() => {});
  };

  useEffect(() => {
    Promise.all([
      api.get(`/marketplace/listings/${listingId}`),
      api.get("/marketplace/lenders"),
    ]).then(([dRes, lRes]) => {
      setDetail(dRes.data);
      setLenders(lRes.data);
      if (lRes.data.length > 0) setFundForm((f) => ({ ...f, lender_id: lRes.data[0].id }));
      setLoading(false);
      if (["funded", "settled"].includes(dRes.data.listing_status)) {
        fetchRepayments();
      }
      fetchActivity();
      // Check for existing negotiations on this listing
      api.get(`/negotiate/listing/${listingId}`).then((r) => setListingNegotiations(r.data || [])).catch(() => {});
    }).catch(() => setLoading(false));
  }, [listingId]);

  const openNegotiationChat = async () => {
    setChatLoading(true);
    try {
      const r = await api.post(`/negotiate/${listingId}/start`);
      setChatSession(r.data);
      setShowChat(true);
      // Pre-fill offer form: use remaining amount (Community Pot), not full invoice
      setOfferForm({ rate: r.data.max_interest_rate || 15, amount: r.data.remaining_amount || r.data.invoice_amount || 0, message: "" });
      toast.success("Negotiation chat started! Send your first offer.");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to start negotiation"));
    }
    setChatLoading(false);
  };

  const sendOffer = async () => {
    if (!chatSession) return;
    setSendingOffer(true);
    try {
      const r = await api.post(`/negotiate/${chatSession.session_id}/offer`, {
        rate: offerForm.rate,
        amount: offerForm.amount,
        message: offerForm.message || "",
      });
      setChatSession(r.data);
      setOfferForm((f) => ({ ...f, message: "" }));
      if (r.data.status === "accepted") {
        toast.success(`Deal accepted at ${r.data.final_rate}%!`);
      } else if (r.data.status === "rejected") {
        toast.error("Negotiation ended — no agreement reached.");
      }
      // Refresh listing negotiations
      api.get(`/negotiate/listing/${listingId}`).then((res) => setListingNegotiations(res.data || [])).catch(() => {});
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to send offer"));
    }
    setSendingOffer(false);
  };

  const resumeChat = (session: NegotiationChat) => {
    setChatSession(session);
    setOfferForm({ rate: session.max_interest_rate || 15, amount: session.remaining_amount || session.invoice_amount || 0, message: "" });
    setShowChat(true);
  };

  const acceptAndFund = () => {
    if (!chatSession || chatSession.status !== "accepted") return;
    // Use negotiated slice amount — Community Pot compatible
    const matchedLender = lenders.find((l) => l.id === chatSession.lender.id);
    setFundForm({
      lender_id: matchedLender?.id || (lenders[0]?.id ?? 0),
      funded_amount: chatSession.final_amount || chatSession.remaining_amount || chatSession.invoice_amount,
      offered_interest_rate: chatSession.final_rate || chatSession.max_interest_rate,
    });
    setShowChat(false);
    setShowFund(true);
    toast.success(`Deal accepted at ${chatSession.final_rate}%! Complete your investment.`);
  };

  const requestPdf = async () => {
    setPdfLoading(true);
    try {
      const r = await api.get(`/marketplace/listings/${listingId}/invoice-pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `invoice_${detail?.invoice_number || listingId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Invoice PDF downloaded — blockchain verified!");
    } catch {
      toast.error("Failed to fetch invoice PDF");
    }
    setPdfLoading(false);
  };

  const downloadSmartContract = async () => {
    setContractLoading(true);
    try {
      const r = await api.get(`/marketplace/listings/${listingId}/smart-contract-pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `SmartContract_${detail?.invoice_number || listingId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Smart Contract PDF downloaded!");
    } catch {
      toast.error("Failed to download smart contract");
    }
    setContractLoading(false);
  };

  const requestGst = async () => {
    setGstLoading(true);
    try {
      const r = await api.get(`/marketplace/listings/${listingId}/gst-filings`);
      setGstData(r.data);
      toast.success("GST filings retrieved");
    } catch {
      toast.error("Failed to fetch GST filings");
    }
    setGstLoading(false);
  };

  const fundInvoice = async () => {
    if (!fundForm.lender_id || !fundForm.funded_amount || !fundForm.offered_interest_rate) {
      toast.error("All fields are required");
      return;
    }
    setFunding(true);
    try {
      // Create order on backend
      const orderData = await createFundingOrder({
        listing_id: Number(listingId),
        lender_id: fundForm.lender_id,
        funded_amount: fundForm.funded_amount,
        offered_interest_rate: fundForm.offered_interest_rate,
      });

      // Open InvoX Pay checkout
      setCheckoutOrder(orderData);
      setCheckoutContext({ type: "funding" });
      setShowFund(false);
      setFunding(false);
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to create payment order"));
      setFunding(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-[#f8f9fc] flex items-center justify-center">
      <div className="text-center">
        <div className="relative inline-block">
          <div className="w-16 h-16 border-4 border-indigo-100 rounded-full" />
          <div className="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin absolute inset-0" />
        </div>
        <p className="text-sm text-gray-500 mt-4">Loading listing details...</p>
      </div>
    </div>
  );

  if (!detail) return (
    <div className="min-h-screen bg-[#f8f9fc] flex items-center justify-center flex-col gap-3">
      <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center">
        <AlertCircle className="w-8 h-8 text-red-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900">Listing not found</h3>
      <Link href="/marketplace" className="text-sm text-indigo-600 hover:underline">← Back to marketplace</Link>
    </div>
  );

  const inputCls = "w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all bg-white";
  const isOpen = detail.listing_status === "open" || detail.listing_status === "partially_funded";
  const st = statusConfig[detail.listing_status] || statusConfig.open;
  const risk = riskMeter(detail.risk_score);
  const cibil = cibilGrade(detail.cibil_score);
  const catIcon = categoryIcons[detail.business_category || ""] || "🏢";
  const yearsInBiz = detail.year_of_establishment ? new Date().getFullYear() - detail.year_of_establishment : null;
  const images = detail.business_images || [];
  const gradBg = gradientBgs[(detail.id || 0) % gradientBgs.length];

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-[#f8f9fc]">
      {/* ─── Sticky Header ─── */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
          <div className="flex items-center gap-4">
            <Link href="/marketplace" className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </Link>
            <div className="hidden sm:block">
              <p className="text-sm font-semibold text-gray-900">{detail.business_name}</p>
              <p className="text-[11px] text-gray-400">Invoice {detail.invoice_number}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isOpen && isLender && (
              <button onClick={() => setShowFund(true)}
                className="inline-flex items-center gap-1.5 px-5 py-2 bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-xl text-xs font-semibold hover:shadow-lg hover:shadow-green-200 transition-all active:scale-[0.98]">
                <HandCoins className="w-4 h-4" /> Fund This Invoice
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ─── Hero Banner ─── */}
      <div className="relative">
        {images.length > 0 ? (
          <div className="relative h-72 sm:h-80 overflow-hidden">
            <img src={fileUrl(images[imageIdx])} alt={detail.business_name} className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
            {images.length > 1 && (
              <>
                <button onClick={() => setImageIdx((i) => (i - 1 + images.length) % images.length)}
                  className="absolute left-4 top-1/2 -translate-y-1/2 p-2 bg-white/20 backdrop-blur-sm rounded-full hover:bg-white/40 transition-colors">
                  <ChevronLeft className="w-5 h-5 text-white" />
                </button>
                <button onClick={() => setImageIdx((i) => (i + 1) % images.length)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 p-2 bg-white/20 backdrop-blur-sm rounded-full hover:bg-white/40 transition-colors">
                  <ChevronRight className="w-5 h-5 text-white" />
                </button>
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1.5">
                  {images.map((_: string, i: number) => (
                    <button key={i} onClick={() => setImageIdx(i)}
                      className={`w-2 h-2 rounded-full transition-all ${i === imageIdx ? "bg-white w-6" : "bg-white/50"}`} />
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <div className={`h-56 sm:h-64 bg-gradient-to-br ${gradBg} relative overflow-hidden`}>
            <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }} />
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-7xl">{catIcon}</span>
            </div>
          </div>
        )}

        {/* Floating status badge */}
        <div className="absolute top-4 right-4">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold backdrop-blur-md shadow-lg ${st.bg} ${st.text}`}>
            <span className={`w-2 h-2 rounded-full ${st.dot} animate-pulse`} /> {st.label}
          </span>
        </div>

        {/* Blockchain badge */}
        {detail.blockchain_hash && (
          <div className="absolute top-4 left-4">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-white/90 backdrop-blur-md text-indigo-700 shadow-lg">
              <Shield className="w-3.5 h-3.5" /> Blockchain Secured
            </span>
          </div>
        )}
      </div>

      {/* ─── Main Content ─── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-12 relative z-10 pb-12">
        {/* Business Identity Card */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-xl shadow-gray-100/50 p-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className={`w-16 h-16 bg-gradient-to-br ${gradBg} rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg`}>
                <span className="text-3xl">{catIcon}</span>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-2xl font-bold text-gray-900">{detail.business_name}</h1>
                  {detail.profile_status === "verified" && (
                    <BadgeCheck className="w-5 h-5 text-indigo-500" />
                  )}
                </div>
                <p className="text-sm text-gray-500">{detail.vendor_name}</p>
                <div className="flex items-center gap-3 mt-2 flex-wrap text-xs text-gray-400">
                  {detail.business_city && (
                    <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {detail.business_city}, {detail.business_state}</span>
                  )}
                  {detail.business_category && (
                    <span className="flex items-center gap-1"><Briefcase className="w-3 h-3" /> {detail.business_category}</span>
                  )}
                  {detail.business_type && (
                    <span className="flex items-center gap-1"><Building2 className="w-3 h-3" /> {detail.business_type}</span>
                  )}
                  {yearsInBiz !== null && (
                    <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> Est. {detail.year_of_establishment} ({yearsInBiz} yrs)</span>
                  )}
                  {detail.number_of_employees && (
                    <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {detail.number_of_employees} employees</span>
                  )}
                </div>
                {detail.listing_title && (
                  <p className="text-base font-semibold text-indigo-700 mt-2">{detail.listing_title}</p>
                )}
                {detail.listing_description && (
                  <p className="text-sm text-gray-600 mt-1 leading-relaxed max-w-2xl bg-indigo-50 border border-indigo-100 rounded-lg p-3">{detail.listing_description}</p>
                )}
                {detail.business_description && !detail.listing_description && (
                  <p className="text-sm text-gray-600 mt-3 leading-relaxed max-w-2xl">{detail.business_description}</p>
                )}
              </div>
            </div>

            {/* Quick stats */}
            <div className="flex items-center gap-4 flex-shrink-0">
              {/* Rating */}
              <div className="text-center">
                <div className="flex items-center gap-1 mb-0.5">
                  <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                  <span className="text-lg font-bold text-gray-900">{(detail.average_rating || 0).toFixed(1)}</span>
                </div>
                <p className="text-[10px] text-gray-400">{detail.total_reviews || 0} reviews</p>
              </div>

              {/* CIBIL */}
              <div className={`text-center px-3 py-2 rounded-xl ring-1 ${cibil.ring} ${cibil.bg}`}>
                <p className={`text-xl font-bold ${cibil.color}`}>{detail.cibil_score || "—"}</p>
                <p className="text-[10px] text-gray-500 font-medium">{cibil.grade}</p>
              </div>

              {/* Deals */}
              <div className="text-center">
                <p className="text-lg font-bold text-gray-900">{detail.total_funded_deals || 0}</p>
                <p className="text-[10px] text-gray-400">Funded Deals</p>
              </div>
            </div>
          </div>
        </div>

        {/* ─── Key Metrics Strip ─── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-2xl border border-gray-100 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-2 text-gray-400 text-[11px] mb-2 uppercase tracking-wider font-medium">
              <IndianRupee className="w-3.5 h-3.5" /> Funding Ask
            </div>
            <p className="text-2xl font-bold text-gray-900">₹{detail.requested_amount.toLocaleString("en-IN")}</p>
            <p className="text-[11px] text-gray-400 mt-0.5">of ₹{(detail.grand_total ?? 0).toLocaleString("en-IN")} invoice</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-100 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-2 text-gray-400 text-[11px] mb-2 uppercase tracking-wider font-medium">
              <Percent className="w-3.5 h-3.5" /> Max Returns
            </div>
            <p className="text-2xl font-bold text-emerald-600">{detail.max_interest_rate}%</p>
            <p className="text-[11px] text-gray-400 mt-0.5">per annum</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-100 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-2 text-gray-400 text-[11px] mb-2 uppercase tracking-wider font-medium">
              <Clock className="w-3.5 h-3.5" /> Tenure
            </div>
            <p className="text-2xl font-bold text-gray-900">{detail.repayment_period_days}</p>
            <p className="text-[11px] text-gray-400 mt-0.5">days to repay</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-100 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-2 text-gray-400 text-[11px] mb-2 uppercase tracking-wider font-medium">
              <TrendingUp className="w-3.5 h-3.5" /> Turnover
            </div>
            <p className="text-2xl font-bold text-gray-900">₹{((detail.annual_turnover ?? 0) / 100000).toFixed(1)}L</p>
            <p className="text-[11px] text-gray-400 mt-0.5">annual revenue</p>
          </div>
        </div>

        {/* ─── Two Column Layout ─── */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left column (2/3) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Tab navigation */}
            <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
              <div className="border-b border-gray-100 px-6 flex gap-0">
                {[
                  { key: "overview" as const, label: "Overview", icon: Eye },
                  { key: "financials" as const, label: "Financials", icon: BarChart3 },
                  { key: "invoice" as const, label: "Invoice Details", icon: FileText },
                  { key: "activity" as const, label: "Activity", icon: Activity },
                ].map((tab) => (
                  <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                    className={`inline-flex items-center gap-1.5 px-4 py-3.5 text-xs font-semibold border-b-2 transition-all ${
                      activeTab === tab.key
                        ? "border-indigo-600 text-indigo-600"
                        : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-200"
                    }`}>
                    <tab.icon className="w-3.5 h-3.5" /> {tab.label}
                  </button>
                ))}
              </div>

              <div className="p-6">
                {/* OVERVIEW TAB */}
                {activeTab === "overview" && (
                  <div className="space-y-6">
                    {/* Risk Assessment */}
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Gauge className="w-4 h-4 text-indigo-500" /> AI Risk Assessment
                      </h3>
                      <div className="bg-gray-50 rounded-xl p-5">
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <p className={`text-2xl font-bold ${risk.color}`}>{detail.risk_score?.toFixed(1) ?? "—"}<span className="text-sm font-normal text-gray-400">/100</span></p>
                            <p className={`text-xs font-semibold ${risk.color}`}>{risk.label} Risk</p>
                          </div>
                          <div className="text-right text-[11px] text-gray-500 space-y-0.5">
                            <p>🟢 0-25 Very Low</p>
                            <p>🟡 26-55 Moderate</p>
                            <p>🔴 56-100 High</p>
                          </div>
                        </div>
                        <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full bg-gradient-to-r ${risk.fill} transition-all duration-1000`}
                            style={{ width: `${detail.risk_score ?? 50}%` }} />
                        </div>
                        <div className="grid grid-cols-4 gap-2 mt-4 text-[10px] text-gray-500">
                          <div className="text-center">
                            <p className="font-semibold text-gray-700">CIBIL</p>
                            <p>{detail.cibil_score ?? "—"}</p>
                          </div>
                          <div className="text-center">
                            <p className="font-semibold text-gray-700">GST Status</p>
                            <p className="capitalize">{detail.gst_compliance_status || "—"}</p>
                          </div>
                          <div className="text-center">
                            <p className="font-semibold text-gray-700">Business Age</p>
                            <p>{yearsInBiz ? `${yearsInBiz} years` : "—"}</p>
                          </div>
                          <div className="text-center">
                            <p className="font-semibold text-gray-700">Verification</p>
                            <p className="capitalize">{detail.profile_status || "—"}</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Business Details */}
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-indigo-500" /> Business Profile
                      </h3>
                      <div className="grid sm:grid-cols-2 gap-3">
                        {[
                          { label: "GSTIN", value: detail.vendor_gstin, mono: true },
                          { label: "State", value: detail.vendor_state },
                          { label: "Category", value: detail.business_category },
                          { label: "Type", value: detail.business_type },
                          { label: "Established", value: detail.year_of_establishment?.toString() },
                          { label: "Employees", value: detail.number_of_employees?.toString() },
                          { label: "GST Filing", value: detail.gst_filing_frequency },
                          { label: "Total GST Filings", value: detail.total_gst_filings?.toString() },
                        ].map((item) => (
                          <div key={item.label} className="flex justify-between items-center py-2.5 px-3 bg-gray-50 rounded-lg">
                            <span className="text-xs text-gray-500">{item.label}</span>
                            <span className={`text-xs font-semibold text-gray-900 ${item.mono ? "font-mono text-[11px]" : ""}`}>
                              {item.value || "—"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* GST Compliance */}
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Globe className="w-4 h-4 text-indigo-500" /> GST Compliance
                      </h3>
                      <div className="flex items-center gap-3">
                        <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold ${
                          (detail.gst_compliance_status || "").toLowerCase() === "regular" ? "bg-emerald-50 text-emerald-700" :
                          (detail.gst_compliance_status || "").toLowerCase() === "irregular" ? "bg-yellow-50 text-yellow-700" :
                          "bg-red-50 text-red-700"
                        }`}>
                          {(detail.gst_compliance_status || "").toLowerCase() === "regular" ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                          {detail.gst_compliance_status || "Unknown"}
                        </span>
                        <span className="text-xs text-gray-500">{detail.total_gst_filings ?? 0} filings · {detail.gst_filing_frequency || "N/A"} frequency</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* FINANCIALS TAB */}
                {activeTab === "financials" && (
                  <div className="space-y-6">
                    <div className="grid sm:grid-cols-2 gap-4">
                      {[
                        { label: "CIBIL Score", value: detail.cibil_score?.toString() ?? "—", sub: cibil.grade, color: cibil.color },
                        { label: "Annual Turnover", value: `₹${(detail.annual_turnover ?? 0).toLocaleString("en-IN")}`, sub: "Yearly revenue", color: "text-gray-900" },
                        { label: "Monthly Revenue", value: `₹${(detail.monthly_revenue ?? 0).toLocaleString("en-IN")}`, sub: "Monthly income", color: "text-gray-900" },
                        { label: "Existing Liabilities", value: `₹${(detail.existing_liabilities ?? 0).toLocaleString("en-IN")}`, sub: "Outstanding debt", color: detail.existing_liabilities && detail.existing_liabilities > 0 ? "text-orange-600" : "text-gray-900" },
                      ].map((item) => (
                        <div key={item.label} className="bg-gray-50 rounded-xl p-4">
                          <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium mb-1">{item.label}</p>
                          <p className={`text-xl font-bold ${item.color}`}>{item.value}</p>
                          <p className="text-[11px] text-gray-400 mt-0.5">{item.sub}</p>
                        </div>
                      ))}
                    </div>

                    {/* Debt-to-income ratio */}
                    {detail.annual_turnover && detail.annual_turnover > 0 && (
                      <div className="bg-gray-50 rounded-xl p-4">
                        <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium mb-2">Debt-to-Turnover Ratio</p>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-emerald-400 to-amber-400 rounded-full"
                              style={{ width: `${Math.min(100, ((detail.existing_liabilities ?? 0) / detail.annual_turnover) * 100)}%` }} />
                          </div>
                          <span className="text-sm font-bold text-gray-700">
                            {(((detail.existing_liabilities ?? 0) / detail.annual_turnover) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Listing financials */}
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 mb-3">Listing Terms</h3>
                      <div className="space-y-2">
                        {[
                          { label: "Requested Percentage", value: `${detail.requested_percentage}%` },
                          { label: "Requested Amount", value: `₹${detail.requested_amount.toLocaleString("en-IN")}` },
                          { label: "Max Interest Rate", value: `${detail.max_interest_rate}% p.a.` },
                          { label: "Discount Rate", value: detail.discount_rate ? `${detail.discount_rate}%` : "—" },
                          { label: "Repayment Period", value: `${detail.repayment_period_days} days` },
                        ].map((item) => (
                          <div key={item.label} className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
                            <span className="text-xs text-gray-500">{item.label}</span>
                            <span className="text-xs font-semibold text-gray-900">{item.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {(detail.listing_status === "funded" || detail.listing_status === "partially_funded") && (detail.total_funded_amount || 0) > 0 && (
                      <div className={`${detail.listing_status === "funded" ? "bg-emerald-50 border-emerald-200" : "bg-amber-50 border-amber-200"} border rounded-xl p-4`}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <CheckCircle className={`w-4 h-4 ${detail.listing_status === "funded" ? "text-emerald-600" : "text-amber-600"}`} />
                            <p className={`text-sm font-semibold ${detail.listing_status === "funded" ? "text-emerald-800" : "text-amber-800"}`}>
                              {detail.listing_status === "funded" ? "Fully Funded" : "Funding In Progress"}
                            </p>
                          </div>
                          <span className="text-xs font-bold text-gray-500">{detail.total_investors || 0} investor{(detail.total_investors || 0) !== 1 ? "s" : ""}</span>
                        </div>
                        <div className="w-full h-2 bg-white/60 rounded-full overflow-hidden mb-2">
                          <div className={`h-full rounded-full ${detail.listing_status === "funded" ? "bg-emerald-500" : "bg-amber-500"}`}
                            style={{ width: `${Math.min(100, detail.funding_progress_pct || 0)}%` }} />
                        </div>
                        <div className="grid sm:grid-cols-3 gap-3 text-xs">
                          <div><span className={detail.listing_status === "funded" ? "text-emerald-600" : "text-amber-600"}>Raised:</span> <span className="font-bold">₹{(detail.total_funded_amount || 0).toLocaleString("en-IN")}</span></div>
                          <div><span className={detail.listing_status === "funded" ? "text-emerald-600" : "text-amber-600"}>Target:</span> <span className="font-bold">₹{detail.requested_amount.toLocaleString("en-IN")}</span></div>
                          <div><span className={detail.listing_status === "funded" ? "text-emerald-600" : "text-amber-600"}>Progress:</span> <span className="font-bold">{(detail.funding_progress_pct || 0).toFixed(1)}%</span></div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* INVOICE TAB */}
                {activeTab === "invoice" && (
                  <div className="space-y-6">
                    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {[
                        { label: "Invoice #", value: detail.invoice_number },
                        { label: "Date", value: detail.invoice_date ? new Date(detail.invoice_date).toLocaleDateString("en-IN") : "—" },
                        { label: "Due Date", value: detail.due_date ? new Date(detail.due_date).toLocaleDateString("en-IN") : "—" },
                        { label: "Buyer", value: detail.buyer_name },
                        { label: "Buyer GSTIN", value: detail.buyer_gstin, mono: true },
                        { label: "Supply Type", value: detail.supply_type?.replace("_", " ") },
                        { label: "Grand Total", value: `₹${(detail.grand_total ?? 0).toLocaleString("en-IN")}` },
                        { label: "Requested %", value: `${detail.requested_percentage}%` },
                      ].map((item) => (
                        <div key={item.label} className="flex justify-between items-center py-2.5 px-3 bg-gray-50 rounded-lg">
                          <span className="text-xs text-gray-500">{item.label}</span>
                          <span className={`text-xs font-semibold text-gray-900 capitalize ${item.mono ? "font-mono text-[11px]" : ""}`}>
                            {item.value || "—"}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Document actions */}
                    <div className="flex flex-wrap gap-3">
                      <button onClick={requestPdf} disabled={pdfLoading}
                        className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-semibold hover:bg-indigo-700 disabled:opacity-60 transition-all">
                        {pdfLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        Download Invoice PDF
                      </button>
                      <button onClick={requestGst} disabled={gstLoading}
                        className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-500 text-white rounded-xl text-xs font-semibold hover:bg-amber-600 disabled:opacity-60 transition-all">
                        {gstLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileBarChart2 className="w-4 h-4" />}
                        Request GST Filing
                      </button>
                    </div>

                    {/* GST data if loaded */}
                    {gstData && (
                      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                        <h4 className="text-xs font-bold text-amber-800 mb-3 flex items-center gap-1.5">
                          <Globe className="w-3.5 h-3.5" /> GST Filing Details
                        </h4>
                        <div className="grid sm:grid-cols-2 gap-2 text-xs">
                          <div><span className="text-amber-700">GSTIN:</span> <span className="font-mono">{String(gstData.gstin ?? "—")}</span></div>
                          <div><span className="text-amber-700">Compliance:</span> <span className="font-semibold capitalize">{String(gstData.gst_compliance_status ?? "Unknown")}</span></div>
                          <div><span className="text-amber-700">Frequency:</span> <span className="capitalize">{String(gstData.filing_frequency ?? gstData.gst_filing_frequency ?? "—")}</span></div>
                          <div><span className="text-amber-700">Total Filings:</span> {String(gstData.total_filings ?? gstData.total_gst_filings ?? 0)}</div>
                        </div>
                        {Boolean(gstData.blockchain_recorded) && (
                          <p className="mt-2 text-[11px] text-indigo-600 flex items-center gap-1"><Shield className="w-3 h-3" /> Recorded on blockchain</p>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* ACTIVITY TAB */}
                {activeTab === "activity" && (
                  <div>
                    {activities.length === 0 ? (
                      <div className="text-center py-12">
                        <Activity className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                        <p className="text-sm text-gray-500">No activity yet</p>
                      </div>
                    ) : (
                      <div className="space-y-0">
                        {activities.map((a, idx) => (
                          <div key={a.id} className="flex gap-3 py-3 border-b border-gray-50 last:border-0">
                            <div className="flex flex-col items-center">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                                a.action === "funded" ? "bg-emerald-100" :
                                a.action === "listed" ? "bg-indigo-100" :
                                a.action === "settled" ? "bg-blue-100" : "bg-gray-100"
                              }`}>
                                {a.action === "funded" ? <CircleDollarSign className="w-4 h-4 text-emerald-600" /> :
                                 a.action === "listed" ? <FileText className="w-4 h-4 text-indigo-600" /> :
                                 <Activity className="w-4 h-4 text-gray-500" />}
                              </div>
                              {idx < activities.length - 1 && <div className="w-px h-full bg-gray-100 mt-1" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-semibold text-gray-900">{a.action}</p>
                              <p className="text-[11px] text-gray-500 mt-0.5">{a.description}</p>
                              {a.created_at && (
                                <p className="text-[10px] text-gray-400 mt-1">{new Date(a.created_at).toLocaleString("en-IN")}</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Repayment Schedule */}
            {repayments.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                    <CreditCard className="w-4 h-4 text-emerald-500" /> Repayment Schedule
                  </h3>
                  <span className="text-xs text-gray-400">{repayments.filter(r => r.status === "paid").length}/{repayments.length} paid</span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-100 rounded-full h-2.5 mb-5">
                  <div className="bg-gradient-to-r from-emerald-400 to-emerald-600 h-2.5 rounded-full transition-all duration-500"
                    style={{ width: `${(repayments.filter(r => r.status === "paid").length / repayments.length) * 100}%` }} />
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-500 border-b border-gray-100">
                        <th className="text-left py-2.5 font-semibold">#</th>
                        <th className="text-left py-2.5 font-semibold">Due Date</th>
                        <th className="text-right py-2.5 font-semibold">Principal</th>
                        <th className="text-right py-2.5 font-semibold">Interest</th>
                        <th className="text-right py-2.5 font-semibold">Total</th>
                        <th className="text-center py-2.5 font-semibold">Status</th>
                        <th className="text-right py-2.5 font-semibold">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {repayments.map((inst) => (
                        <tr key={inst.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50/50">
                          <td className="py-3">{inst.installment_number}</td>
                          <td className="py-3">{new Date(inst.due_date).toLocaleDateString("en-IN")}</td>
                          <td className="py-3 text-right">₹{inst.principal_amount.toLocaleString("en-IN")}</td>
                          <td className="py-3 text-right">₹{inst.interest_amount.toLocaleString("en-IN")}</td>
                          <td className="py-3 text-right font-semibold">₹{inst.total_amount.toLocaleString("en-IN")}</td>
                          <td className="py-3 text-center">
                            <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold ${
                              inst.status === "paid" ? "bg-emerald-100 text-emerald-700" :
                              inst.status === "overdue" ? "bg-red-100 text-red-700" :
                              "bg-amber-100 text-amber-800"
                            }`}>{inst.status}</span>
                          </td>
                          <td className="py-3 text-right">
                            {(inst.status === "pending" || inst.status === "overdue") && (
                              <button
                                disabled={payingId === inst.id}
                                onClick={async () => {
                                  setPayingId(inst.id);
                                  try {
                                    // Create repayment order
                                    const orderData = await createRepaymentOrder({
                                      listing_id: Number(listingId),
                                      installment_id: inst.id,
                                    });

                                    // Open InvoX Pay checkout
                                    setCheckoutOrder(orderData);
                                    setCheckoutContext({ type: "repayment", installment_number: inst.installment_number });
                                    setPayingId(null);
                                  } catch (err: unknown) {
                                    toast.error(getErrorMessage(err, "Failed to create payment"));
                                    setPayingId(null);
                                  }
                                }}
                                className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-[10px] font-semibold hover:bg-emerald-700 disabled:opacity-60 inline-flex items-center gap-1 transition-all">
                                {payingId === inst.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CreditCard className="w-3 h-3" />}
                                Pay via InvoX Pay
                              </button>
                            )}
                            {inst.status === "paid" && (
                              <span className="text-[10px] text-emerald-600 font-medium">
                                {inst.paid_date ? new Date(inst.paid_date).toLocaleDateString("en-IN") : "Paid"}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 pt-3 border-t border-gray-100 flex justify-between text-[11px] text-gray-500">
                  <span>Total Principal: ₹{repayments.reduce((s, i) => s + i.principal_amount, 0).toLocaleString("en-IN")}</span>
                  <span>Total Interest: ₹{repayments.reduce((s, i) => s + i.interest_amount, 0).toLocaleString("en-IN")}</span>
                  <span className="font-bold text-gray-700">Grand Total: ₹{repayments.reduce((s, i) => s + i.total_amount, 0).toLocaleString("en-IN")}</span>
                </div>

                {/* Pay All Remaining Installments */}
                {repayments.some(r => r.status === "pending" || r.status === "overdue") && (
                  <div className="mt-4 pt-3 border-t border-gray-100">
                    <button
                      disabled={payingAll}
                      onClick={async () => {
                        setPayingAll(true);
                        try {
                          const orderData = await createPayAllOrder({ listing_id: Number(listingId) });
                          setCheckoutOrder(orderData);
                          setCheckoutContext({ type: "repayment_all" });
                          setPayingAll(false);
                        } catch (err: unknown) {
                          toast.error(getErrorMessage(err, "Failed to create pay-all order"));
                          setPayingAll(false);
                        }
                      }}
                      className="w-full py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-sm font-bold hover:shadow-lg hover:shadow-indigo-200 disabled:opacity-60 inline-flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                    >
                      {payingAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                      Pay All Remaining (₹{repayments.filter(r => r.status !== "paid").reduce((s, i) => s + i.total_amount, 0).toLocaleString("en-IN")})
                    </button>
                    <p className="text-center text-[10px] text-gray-400 mt-2 flex items-center justify-center gap-1">
                      <Lock className="w-3 h-3" /> Settle all installments at once via InvoX Pay
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right column (1/3) — Sidebar */}
          <div className="space-y-5">
            {/* ── Community Pot Progress Card ── */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-lg p-6">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Users className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-gray-900">Community Pot</h3>
                  <p className="text-[10px] text-gray-400">Fractional Investment Pool</p>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xl font-bold text-gray-900">{detail.funding_progress_pct?.toFixed(0) || 0}%</span>
                  <span className="text-xs text-gray-500">
                    {detail.total_investors || 0} Investor{(detail.total_investors || 0) !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ease-out ${
                      (detail.funding_progress_pct || 0) >= 100
                        ? "bg-gradient-to-r from-emerald-400 to-green-500"
                        : (detail.funding_progress_pct || 0) >= 50
                        ? "bg-gradient-to-r from-indigo-400 to-purple-500"
                        : "bg-gradient-to-r from-blue-400 to-indigo-500"
                    }`}
                    style={{ width: `${Math.min(100, detail.funding_progress_pct || 0)}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1.5">
                  <span className="text-[11px] text-gray-500">₹{(detail.total_funded_amount || 0).toLocaleString("en-IN")} raised</span>
                  <span className="text-[11px] text-gray-500">of ₹{detail.requested_amount.toLocaleString("en-IN")}</span>
                </div>
              </div>

              {/* Investors list preview */}
              {detail.investors && detail.investors.length > 0 && (
                <div className="border-t border-gray-100 pt-3 mt-3">
                  <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Recent Investors</p>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {detail.investors.slice(0, 5).map((inv) => (
                      <div key={inv.id} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center">
                            <span className="text-[10px] font-bold text-indigo-600">{inv.lender_name.charAt(0)}</span>
                          </div>
                          <div>
                            <span className="font-semibold text-gray-800">{inv.lender_name}</span>
                            <span className="text-[10px] text-gray-400 ml-1">({inv.ownership_percentage}%)</span>
                          </div>
                        </div>
                        <span className="font-bold text-gray-700">₹{inv.invested_amount.toLocaleString("en-IN")}</span>
                      </div>
                    ))}
                    {detail.investors.length > 5 && (
                      <p className="text-[10px] text-indigo-500 text-center pt-1">+{detail.investors.length - 5} more investors</p>
                    )}
                  </div>
                </div>
              )}

              {isOpen && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Remaining</span>
                    <span className="font-bold text-indigo-600">₹{(detail.remaining_amount || 0).toLocaleString("en-IN")}</span>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Min. Investment</span>
                    <span className="font-bold text-gray-700">₹{(detail.min_investment || 500).toLocaleString("en-IN")}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Fund CTA Card */}
            {isOpen && isLender && (
              <div className="bg-gradient-to-br from-emerald-500 to-green-600 rounded-2xl p-6 text-white shadow-xl shadow-emerald-100">
                <div className="flex items-center gap-2 mb-3">
                  <CircleDollarSign className="w-5 h-5" />
                  <h3 className="text-base font-bold">Invest in This Invoice</h3>
                </div>
                <p className="text-emerald-100 text-xs mb-4 leading-relaxed">
                  Earn up to {detail.max_interest_rate}% returns by investing as little as ₹{(detail.min_investment || 500).toLocaleString("en-IN")} in this blockchain-verified invoice.
                </p>
                <div className="bg-white/15 backdrop-blur-sm rounded-xl p-3 mb-4 space-y-1.5 text-xs">
                  <div className="flex justify-between"><span className="text-white/80">Total Ask</span><span className="font-bold">₹{detail.requested_amount.toLocaleString("en-IN")}</span></div>
                  <div className="flex justify-between"><span className="text-white/80">Remaining</span><span className="font-bold">₹{(detail.remaining_amount || detail.requested_amount).toLocaleString("en-IN")}</span></div>
                  <div className="flex justify-between"><span className="text-white/80">Max Returns</span><span className="font-bold">{detail.max_interest_rate}% p.a.</span></div>
                  <div className="flex justify-between"><span className="text-white/80">Tenure</span><span className="font-bold">{detail.repayment_period_days} days</span></div>
                  <div className="flex justify-between"><span className="text-white/80">Investors</span><span className="font-bold">{detail.total_investors || 0}</span></div>
                </div>
                <button onClick={() => setShowFund(true)}
                  className="w-full py-3 bg-white text-emerald-700 rounded-xl text-sm font-bold hover:bg-emerald-50 transition-all active:scale-[0.98]">
                  Invest Now →
                </button>
                <div className="flex items-center justify-center gap-1.5 mt-3 text-[10px] text-white/70">
                  <Lock className="w-3 h-3" />
                  <span>Secured by InvoX Pay Gateway</span>
                </div>
              </div>
            )}

            {/* ──── AI NEGOTIATION CHAT ──── */}
            {isOpen && isLender && (
              <div className="bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-700 rounded-2xl p-[1px] shadow-xl shadow-purple-100">
                <div className="bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-700 rounded-2xl p-6 text-white relative overflow-hidden">
                  <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23fff' fill-opacity='0.15'%3E%3Ccircle cx='20' cy='20' r='2'/%3E%3C/g%3E%3C/svg%3E\")" }} />
                  <div className="relative">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-8 h-8 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                        <Bot className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold">AI Negotiator</h3>
                        <p className="text-[10px] text-white/60">Chat with AI Agent</p>
                      </div>
                    </div>

                    <p className="text-violet-100 text-xs mb-4 leading-relaxed">
                      Start a negotiation chat — our AI agent represents the vendor. Send your rate &amp; amount offer, and negotiate in real-time.
                    </p>

                    {/* Existing negotiations on this listing */}
                    {listingNegotiations.length > 0 && (
                      <div className="bg-white/10 backdrop-blur-sm rounded-xl p-3 mb-3">
                        <p className="text-[10px] text-white/60 font-semibold mb-2 uppercase tracking-wider">
                          Your Negotiations ({listingNegotiations.filter(n => n.lender.id === user?.lender_id).length})
                        </p>
                        <div className="space-y-1.5">
                          {listingNegotiations.filter(n => n.lender.id === user?.lender_id).map((neg) => (
                            <button key={neg.session_id} onClick={() => resumeChat(neg)}
                              className="w-full flex items-center justify-between text-[11px] px-2.5 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-all text-left">
                              <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${neg.status === "active" ? "bg-green-400 animate-pulse" : neg.status === "accepted" ? "bg-emerald-400" : "bg-red-400"}`} />
                                <span>Round {neg.current_round}/{neg.max_rounds}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                {neg.final_rate && <span className="font-bold text-emerald-300">{neg.final_rate}%</span>}
                                <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold ${
                                  neg.status === "active" ? "bg-green-400/30 text-green-200" :
                                  neg.status === "accepted" ? "bg-emerald-400/30 text-emerald-200" :
                                  "bg-red-400/30 text-red-200"
                                }`}>{neg.status}</span>
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    <button
                      onClick={openNegotiationChat}
                      disabled={chatLoading}
                      className="w-full py-3 bg-white text-purple-700 rounded-xl text-sm font-bold hover:bg-purple-50 transition-all active:scale-[0.98] disabled:opacity-60 inline-flex items-center justify-center gap-2"
                    >
                      {chatLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Opening chat...
                        </>
                      ) : (
                        <>
                          <MessageSquare className="w-4 h-4" />
                          {listingNegotiations.some(n => n.lender.id === user?.lender_id && n.status === "active")
                            ? "Continue Negotiation" : "Start Negotiation Chat"}
                        </>
                      )}
                    </button>
                    <p className="text-[10px] text-white/40 text-center mt-2">AI agent negotiates on behalf of the vendor</p>
                  </div>
                </div>
              </div>
            )}

            {/* ──── Vendor: View Negotiations on this listing ──── */}
            {isOpen && !isLender && listingNegotiations.length > 0 && (
              <div className="bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-700 rounded-2xl p-[1px] shadow-xl shadow-purple-100">
                <div className="bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-700 rounded-2xl p-6 text-white relative overflow-hidden">
                  <div className="relative">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-8 h-8 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
                        <Bot className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold">AI Negotiations</h3>
                        <p className="text-[10px] text-white/60">{listingNegotiations.length} negotiation(s) on this listing</p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      {listingNegotiations.map((neg) => (
                        <button key={neg.session_id} onClick={() => resumeChat(neg)}
                          className="w-full bg-white/10 hover:bg-white/20 rounded-xl p-3 text-left transition-all">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-semibold">{neg.lender.name}</span>
                            <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold ${
                              neg.status === "active" ? "bg-green-400/30 text-green-200" :
                              neg.status === "accepted" ? "bg-emerald-400/30 text-emerald-200" :
                              "bg-red-400/30 text-red-200"
                            }`}>{neg.status}</span>
                          </div>
                          <div className="flex items-center gap-3 text-[10px] text-white/60">
                            <span>Round {neg.current_round}/{neg.max_rounds}</span>
                            {neg.final_rate && <span className="text-emerald-300 font-semibold">Final: {neg.final_rate}%</span>}
                            <span>{neg.messages.length} messages</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Funded info */}
            {detail.listing_status === "funded" && (detail.total_funded_amount || 0) > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-2xl p-5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-blue-600" />
                    <h3 className="text-sm font-bold text-blue-800">Investment Active</h3>
                  </div>
                  <span className="text-xs font-bold text-blue-500">{detail.total_investors || 0} investor{(detail.total_investors || 0) !== 1 ? "s" : ""}</span>
                </div>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between"><span className="text-blue-600">Total Funded</span><span className="font-bold text-blue-900">₹{(detail.total_funded_amount || 0).toLocaleString("en-IN")}</span></div>
                  <div className="flex justify-between"><span className="text-blue-600">Funding Mode</span><span className="font-bold text-blue-900">Community Pot (Fractional)</span></div>
                  <div className="flex justify-between"><span className="text-blue-600">Date</span><span className="font-bold text-blue-900">{detail.funded_at ? new Date(detail.funded_at).toLocaleDateString("en-IN") : "—"}</span></div>
                </div>

                {/* Refund Button for Lender */}
                {repayments.every(r => r.status !== "paid") && (
                  <div className="mt-4 pt-3 border-t border-blue-200">
                    <button
                      onClick={() => setShowRefund(true)}
                      className="w-full py-2.5 bg-red-50 text-red-600 border border-red-200 rounded-xl text-xs font-semibold hover:bg-red-100 transition-all inline-flex items-center justify-center gap-1.5"
                    >
                      <ArrowLeft className="w-3 h-3" /> Request Refund
                    </button>
                    <p className="text-[10px] text-blue-500 mt-1.5 text-center">Available before repayment starts</p>
                  </div>
                )}
              </div>
            )}

            {/* Blockchain Proof */}
            {detail.blockchain_hash && (
              <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Shield className="w-4 h-4 text-indigo-600" />
                  <h3 className="text-xs font-bold text-indigo-800">Blockchain Verification</h3>
                </div>
                <div className="space-y-2">
                  <div>
                    <p className="text-[10px] text-indigo-500 font-medium mb-0.5">Block Hash</p>
                    <p className="font-mono text-[10px] text-indigo-900 break-all bg-indigo-100/50 p-2 rounded-lg">{detail.blockchain_hash}</p>
                  </div>
                  {detail.pdf_hash && (
                    <div>
                      <p className="text-[10px] text-indigo-500 font-medium mb-0.5">PDF Hash</p>
                      <p className="font-mono text-[10px] text-indigo-900 break-all bg-indigo-100/50 p-2 rounded-lg">{detail.pdf_hash}</p>
                    </div>
                  )}
                  <p className="text-[11px] text-indigo-700 flex items-center gap-1 mt-1">
                    <CheckCircle className="w-3 h-3" /> Immutably recorded on InvoX chain
                  </p>
                </div>
              </div>
            )}

            {/* Trust Signals */}
            <div className="bg-white rounded-2xl border border-gray-100 p-5">
              <h3 className="text-xs font-bold text-gray-900 mb-3">Trust & Safety</h3>
              <div className="space-y-3">
                {[
                  { icon: ShieldCheck, text: "Blockchain-secured invoice", ok: !!detail.blockchain_hash },
                  { icon: BadgeCheck, text: "Vendor identity verified", ok: detail.profile_status === "verified" },
                  { icon: Globe, text: "GST compliance checked", ok: (detail.gst_compliance_status || "").toLowerCase() === "regular" },
                  { icon: Star, text: `CIBIL ${cibil.grade} (${detail.cibil_score || "—"})`, ok: (detail.cibil_score ?? 0) >= 650 },
                  { icon: Lock, text: "Encrypted document storage", ok: true },
                ].map((signal) => (
                  <div key={signal.text} className="flex items-center gap-2.5">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center ${signal.ok ? "bg-emerald-100" : "bg-gray-100"}`}>
                      <signal.icon className={`w-3.5 h-3.5 ${signal.ok ? "text-emerald-600" : "text-gray-400"}`} />
                    </div>
                    <span className={`text-xs ${signal.ok ? "text-gray-700" : "text-gray-400"}`}>{signal.text}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white rounded-2xl border border-gray-100 p-5 space-y-2.5">
              <h3 className="text-xs font-bold text-gray-900 mb-1">Documents</h3>
              <button onClick={requestPdf} disabled={pdfLoading}
                className="w-full inline-flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-xl text-xs font-medium text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-60">
                {pdfLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4 text-indigo-500" />}
                Invoice PDF (Verified)
              </button>
              <button onClick={requestGst} disabled={gstLoading}
                className="w-full inline-flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-xl text-xs font-medium text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-60">
                {gstLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileBarChart2 className="w-4 h-4 text-amber-500" />}
                GST Filing Report
              </button>
              {["funded", "settled"].includes(detail.listing_status) && (
                <button onClick={downloadSmartContract} disabled={contractLoading}
                  className="w-full inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-xl text-xs font-semibold text-indigo-700 hover:from-indigo-100 hover:to-purple-100 transition-all disabled:opacity-60">
                  {contractLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 text-indigo-600" />}
                  Smart Contract PDF
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ─── Refund Modal ─── */}
      {showRefund && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowRefund(false)}>
          <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <ArrowLeft className="w-5 h-5 text-red-500" /> Request Refund
                </h2>
                <p className="text-xs text-gray-500 mt-1">
                  Amount: <span className="font-bold text-red-600">₹{detail.funded_amount?.toLocaleString("en-IN")}</span>
                </p>
              </div>
              <button onClick={() => setShowRefund(false)} className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-4">
              <p className="text-xs text-amber-800 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                Refund is only available before any repayment installments are paid. The listing will reopen for funding.
              </p>
            </div>

            <div className="mb-4">
              <label className="block text-xs font-semibold text-gray-700 mb-1.5">Reason for Refund *</label>
              <textarea
                value={refundReason}
                onChange={(e) => setRefundReason(e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all bg-white resize-none"
                rows={3}
                placeholder="Why are you requesting a refund?"
              />
            </div>

            <div className="flex gap-3">
              <button onClick={() => setShowRefund(false)}
                className="flex-1 px-4 py-3 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors">
                Cancel
              </button>
              <button
                disabled={refunding || !refundReason.trim()}
                onClick={async () => {
                  setRefunding(true);
                  try {
                    const result = await requestRefund({
                      listing_id: Number(listingId),
                      reason: refundReason,
                    });
                    toast.success(`Refund of ₹${result.refund_amount.toLocaleString("en-IN")} processed! Blockchain hash: ${result.blockchain_hash.slice(0, 12)}…`);
                    setShowRefund(false);
                    setRefundReason("Lender requested refund");
                    // Refresh data
                    const r = await api.get(`/marketplace/listings/${listingId}`);
                    setDetail(r.data);
                    setRepayments([]);
                    fetchActivity();
                  } catch (err: unknown) {
                    toast.error(getErrorMessage(err, "Refund failed"));
                  }
                  setRefunding(false);
                }}
                className="flex-1 px-4 py-3 bg-red-600 text-white rounded-xl text-sm font-semibold hover:bg-red-700 disabled:opacity-60 inline-flex items-center justify-center gap-2 transition-all"
              >
                {refunding ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowLeft className="w-4 h-4" />}
                Confirm Refund
              </button>
            </div>

            <div className="flex items-center justify-center gap-2 mt-4 pt-3 border-t border-gray-100">
              <Shield className="w-3 h-3 text-gray-400" />
              <span className="text-[10px] text-gray-400">Refund recorded on <span className="font-semibold text-indigo-600">InvoX blockchain</span></span>
            </div>
          </div>
        </div>
      )}

      {/* ─── Fund Modal ─── */}
      {showFund && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowFund(false)}>
          <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <HandCoins className="w-5 h-5 text-emerald-500" /> Invest in Invoice
                </h2>
                <p className="text-xs text-gray-500 mt-1">
                  Max interest: <span className="font-bold text-emerald-600">{detail.max_interest_rate}%</span> ·
                  Remaining: <span className="font-bold text-indigo-600">₹{(detail.remaining_amount || detail.requested_amount).toLocaleString("en-IN")}</span>
                  <span className="text-gray-400 ml-1">of ₹{detail.requested_amount.toLocaleString("en-IN")}</span>
                </p>
              </div>
              <button onClick={() => setShowFund(false)} className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Select Lender *</label>
                {lenders.length === 0 ? (
                  <p className="text-sm text-red-500">No lenders registered. Register first.</p>
                ) : (
                  <select value={fundForm.lender_id} onChange={(e) => setFundForm({ ...fundForm, lender_id: Number(e.target.value) })}
                    className={inputCls + " cursor-pointer"}>
                    {lenders.map((l) => (
                      <option key={l.id} value={l.id}>{l.name} ({l.organization || l.lender_type})</option>
                    ))}
                  </select>
                )}
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Investment Amount (₹) *</label>
                <input type="number" value={fundForm.funded_amount || ""} onChange={(e) => setFundForm({ ...fundForm, funded_amount: Number(e.target.value) })}
                  className={inputCls} placeholder={`Min ₹${(detail.min_investment || 500).toLocaleString("en-IN")} · Max ₹${(detail.remaining_amount || detail.requested_amount).toLocaleString("en-IN")}`} />
                {fundForm.funded_amount > 0 && fundForm.funded_amount < (detail.min_investment || 500) && (
                  <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Minimum investment is ₹{(detail.min_investment || 500).toLocaleString("en-IN")}
                  </p>
                )}
                {fundForm.funded_amount > (detail.remaining_amount || detail.requested_amount) && (
                  <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Exceeds remaining amount of ₹{(detail.remaining_amount || detail.requested_amount).toLocaleString("en-IN")}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Offered Interest Rate (%) *</label>
                <input type="number" step="0.1" value={fundForm.offered_interest_rate || ""} onChange={(e) => setFundForm({ ...fundForm, offered_interest_rate: Number(e.target.value) })}
                  className={inputCls} placeholder={`Max ${detail.max_interest_rate}%`} />
                {fundForm.offered_interest_rate > detail.max_interest_rate && (
                  <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Exceeds vendor&apos;s max rate of {detail.max_interest_rate}%
                  </p>
                )}
              </div>
            </div>

            {/* Estimated Returns */}
            {fundForm.funded_amount > 0 && fundForm.offered_interest_rate > 0 && (
              <div className="mt-4 bg-emerald-50 border border-emerald-200 rounded-xl p-3">
                <p className="text-[11px] font-semibold text-emerald-800 mb-1">Estimated Returns</p>
                <p className="text-lg font-bold text-emerald-700">
                  ₹{((fundForm.funded_amount * fundForm.offered_interest_rate * detail.repayment_period_days) / (365 * 100)).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                  <span className="text-xs font-normal text-emerald-500 ml-1">interest over {detail.repayment_period_days} days</span>
                </p>
              </div>
            )}

            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowFund(false)}
                className="flex-1 px-4 py-3 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors">
                Cancel
              </button>
              <button onClick={fundInvoice} disabled={funding || lenders.length === 0}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-xl text-sm font-semibold hover:shadow-lg hover:shadow-green-200 disabled:opacity-60 inline-flex items-center justify-center gap-2 transition-all active:scale-[0.98]">
                {funding ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                Pay & Confirm via InvoX Pay
              </button>
            </div>

            {/* InvoX Pay branding */}
            <div className="flex items-center justify-center gap-2 mt-4 pt-3 border-t border-gray-100">
              <Lock className="w-3 h-3 text-gray-400" />
              <span className="text-[10px] text-gray-400">Payments secured by <span className="font-semibold text-indigo-600">InvoX Pay</span> · 256-bit SSL encrypted</span>
            </div>
          </div>
        </div>
      )}

      {/* ─── AI Negotiation Chat Modal ─── */}
      {showChat && chatSession && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => setShowChat(false)}>
          <div className="bg-white rounded-3xl w-full max-w-2xl max-h-[90vh] shadow-2xl flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="p-5 border-b border-gray-100 flex-shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-200">
                    <Bot className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-gray-900">AI Negotiation Chat</h2>
                    <p className="text-xs text-gray-400">
                      {chatSession.lender.name} ↔ {chatSession.vendor.business_name} · Round {chatSession.current_round}/{chatSession.max_rounds}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full ${
                    chatSession.status === "active" ? "bg-green-50 text-green-700 border border-green-200" :
                    chatSession.status === "accepted" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                    chatSession.status === "rejected" ? "bg-red-50 text-red-700 border border-red-200" :
                    "bg-gray-50 text-gray-700 border border-gray-200"
                  }`}>{chatSession.status.toUpperCase()}</span>
                  <button onClick={() => setShowChat(false)} className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
                    <X className="w-5 h-5 text-gray-400" />
                  </button>
                </div>
              </div>

              {/* Context bar — Community Pot aware */}
              <div className="flex gap-2 mt-3">
                <div className="flex-1 bg-gray-50 rounded-lg p-2 text-center">
                  <p className="text-[9px] text-gray-400 uppercase">Full Ask</p>
                  <p className="text-xs font-bold text-gray-900">₹{chatSession.invoice_amount?.toLocaleString("en-IN")}</p>
                </div>
                <div className="flex-1 bg-indigo-50 rounded-lg p-2 text-center">
                  <p className="text-[9px] text-indigo-400 uppercase">Remaining</p>
                  <p className="text-xs font-bold text-indigo-700">₹{(chatSession.remaining_amount || chatSession.invoice_amount)?.toLocaleString("en-IN")}</p>
                </div>
                <div className="flex-1 bg-gray-50 rounded-lg p-2 text-center">
                  <p className="text-[9px] text-gray-400 uppercase">Fair Rate</p>
                  <p className="text-xs font-bold text-gray-900">{chatSession.fair_market_rate}%</p>
                </div>
                <div className="flex-1 bg-gray-50 rounded-lg p-2 text-center">
                  <p className="text-[9px] text-gray-400 uppercase">Max Rate</p>
                  <p className="text-xs font-bold text-gray-900">{chatSession.max_interest_rate}%</p>
                </div>
                {(chatSession.total_investors || 0) > 0 && (
                  <div className="flex-1 bg-purple-50 rounded-lg p-2 text-center">
                    <p className="text-[9px] text-purple-400 uppercase">Investors</p>
                    <p className="text-xs font-bold text-purple-700">{chatSession.total_investors}</p>
                  </div>
                )}
                {chatSession.final_rate && (
                  <div className="flex-1 bg-emerald-50 rounded-lg p-2 text-center">
                    <p className="text-[9px] text-emerald-500 uppercase">Final</p>
                    <p className="text-xs font-bold text-emerald-700">{chatSession.final_rate}%</p>
                  </div>
                )}
              </div>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-5 space-y-3 bg-gray-50/50" id="chat-messages">
              {chatSession.messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.sender === "lender" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[80%] ${msg.sender === "lender" ? "order-1" : ""}`}>
                    <div className="flex items-end gap-2">
                      {msg.sender !== "lender" && (
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                          msg.sender === "ai_agent" ? "bg-gradient-to-br from-violet-500 to-purple-600" : "bg-gray-300"
                        }`}>
                          {msg.sender === "ai_agent" ? <Bot className="w-4 h-4 text-white" /> : <Info className="w-4 h-4 text-gray-500" />}
                        </div>
                      )}
                      <div className={`rounded-2xl px-4 py-3 ${
                        msg.sender === "lender"
                          ? "bg-indigo-600 text-white rounded-br-md"
                          : msg.sender === "ai_agent"
                          ? "bg-white border border-gray-200 text-gray-800 rounded-bl-md shadow-sm"
                          : "bg-gray-200 text-gray-600 rounded-bl-md"
                      }`}>
                        <p className="text-[13px] leading-relaxed whitespace-pre-wrap">{msg.message}</p>
                        {/* Offer details bar */}
                        {msg.offered_rate && (
                          <div className={`flex gap-3 mt-2 pt-2 text-[10px] ${
                            msg.sender === "lender" ? "border-t border-white/20 text-white/70" : "border-t border-gray-100 text-gray-400"
                          }`}>
                            <span>Rate: <span className="font-bold">{msg.offered_rate}%</span></span>
                            {msg.offered_amount && <span>₹{msg.offered_amount.toLocaleString("en-IN")}</span>}
                            {msg.funding_percentage && <span>{msg.funding_percentage}%</span>}
                            {msg.offer_score && <span>Score: {msg.offer_score}/100</span>}
                          </div>
                        )}
                      </div>
                      {msg.sender === "lender" && (
                        <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                          <Building2 className="w-4 h-4 text-indigo-600" />
                        </div>
                      )}
                    </div>
                    <p className={`text-[9px] text-gray-400 mt-1 ${msg.sender === "lender" ? "text-right mr-9" : "ml-9"}`}>
                      {msg.sender === "ai_agent" ? "AI Agent" : msg.sender === "lender" ? "You" : "System"}
                      {msg.created_at && ` · ${new Date(msg.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`}
                    </p>
                  </div>
                </div>
              ))}

              {/* Accepted banner */}
              {chatSession.status === "accepted" && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
                  <div className="flex items-center justify-center gap-2 mb-1">
                    <CheckCircle className="w-5 h-5 text-emerald-600" />
                    <span className="text-sm font-bold text-emerald-800">Deal Accepted!</span>
                  </div>
                  <p className="text-xs text-emerald-600">
                    Final rate: <span className="font-bold">{chatSession.final_rate}%</span> · Amount: <span className="font-bold">₹{chatSession.final_amount?.toLocaleString("en-IN")}</span>
                    {chatSession.final_score && <> · Score: <span className="font-bold">{chatSession.final_score}/100</span></>}
                  </p>
                </div>
              )}
              {chatSession.status === "rejected" && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
                  <div className="flex items-center justify-center gap-2 mb-1">
                    <AlertCircle className="w-5 h-5 text-red-600" />
                    <span className="text-sm font-bold text-red-800">Negotiation Ended</span>
                  </div>
                  <p className="text-xs text-red-600">No agreement was reached. You can start a new negotiation.</p>
                </div>
              )}
            </div>

            {/* Offer Input Form — only if active */}
            {chatSession.status === "active" && isLender && (
              <div className="p-4 border-t border-gray-100 flex-shrink-0 bg-white rounded-b-3xl">
                <div className="flex gap-2 mb-3">
                  <div className="flex-1">
                    <label className="block text-[10px] font-semibold text-gray-500 mb-1 uppercase">Interest Rate (%)</label>
                    <input
                      type="number" step="0.1" value={offerForm.rate || ""}
                      onChange={(e) => setOfferForm({ ...offerForm, rate: Number(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                      placeholder="e.g. 12.5"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-[10px] font-semibold text-gray-500 mb-1 uppercase">Investment Amount (₹)</label>
                    <input
                      type="number" value={offerForm.amount || ""}
                      onChange={(e) => setOfferForm({ ...offerForm, amount: Number(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                      placeholder={`₹${(chatSession.min_investment || 500).toLocaleString("en-IN")} – ₹${(chatSession.remaining_amount || chatSession.invoice_amount)?.toLocaleString("en-IN")}`}
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text" value={offerForm.message}
                    onChange={(e) => setOfferForm({ ...offerForm, message: e.target.value })}
                    className="flex-1 px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                    placeholder="Optional message..."
                    onKeyDown={(e) => { if (e.key === "Enter" && offerForm.rate > 0 && offerForm.amount > 0) sendOffer(); }}
                  />
                  <button
                    onClick={sendOffer}
                    disabled={sendingOffer || offerForm.rate <= 0 || offerForm.amount <= 0}
                    className="px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl text-sm font-bold hover:shadow-lg hover:shadow-indigo-200 disabled:opacity-50 inline-flex items-center gap-2 transition-all active:scale-[0.98]"
                  >
                    {sendingOffer ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                    Send Offer
                  </button>
                </div>
                <p className="text-[10px] text-gray-400 mt-2 text-center">
                  Round {chatSession.current_round}/{chatSession.max_rounds} · AI agent will respond on vendor&apos;s behalf
                </p>
              </div>
            )}

            {/* Accept & Fund button - for accepted deals */}
            {chatSession.status === "accepted" && isLender && (
              <div className="p-4 border-t border-gray-100 flex-shrink-0 bg-white rounded-b-3xl">
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 mb-3 text-xs">
                  <p className="font-semibold text-emerald-800 mb-1">Deal Accepted!</p>
                  <div className="flex justify-between text-emerald-600">
                    <span>Rate: <b>{chatSession.final_rate}%</b></span>
                    <span>Amount: <b>₹{(chatSession.final_amount || 0).toLocaleString("en-IN")}</b></span>
                  </div>
                </div>
                <button
                  onClick={acceptAndFund}
                  className="w-full py-3 bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-xl text-sm font-bold hover:shadow-lg hover:shadow-green-200 transition-all active:scale-[0.98] inline-flex items-center justify-center gap-2"
                >
                  <CheckCircle className="w-4 h-4" /> Invest ₹{(chatSession.final_amount || 0).toLocaleString("en-IN")} at {chatSession.final_rate}%
                </button>
              </div>
            )}

            {/* Vendor view footer */}
            {!isLender && (
              <div className="p-4 border-t border-gray-100 flex-shrink-0 bg-white rounded-b-3xl">
                <p className="text-xs text-gray-500 text-center flex items-center justify-center gap-2">
                  <Bot className="w-4 h-4 text-purple-500" />
                  AI agent is negotiating on your behalf · {chatSession.messages.length} messages
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── InvoX Pay Checkout Modal ─── */}
      {checkoutOrder && (
        <InvoXPayCheckout
          orderData={checkoutOrder}
          onSuccess={async (verifyResult) => {
            setCheckoutOrder(null);
            if (checkoutContext.type === "funding") {
              toast.success(`Invoice funded successfully! Payment ID: ${verifyResult.payment_id || ""}`);
              const r = await api.get(`/marketplace/listings/${listingId}`);
              setDetail(r.data);
              fetchRepayments();
              fetchActivity();
            } else if (checkoutContext.type === "repayment_all") {
              toast.success("All remaining installments paid successfully!");
              fetchRepayments();
              fetchActivity();
              const r = await api.get(`/marketplace/listings/${listingId}`);
              setDetail(r.data);
              if (verifyResult.auto_settled) {
                toast.success("All installments paid! Listing auto-settled.");
              }
            } else {
              toast.success(`Installment #${checkoutContext.installment_number} paid successfully!`);
              fetchRepayments();
              fetchActivity();
              const r = await api.get(`/marketplace/listings/${listingId}`);
              setDetail(r.data);
              if (verifyResult.auto_settled) {
                toast.success("All installments paid! Listing auto-settled.");
              }
            }
          }}
          onFailure={(error) => {
            setCheckoutOrder(null);
            toast.error(error || "Payment failed");
          }}
          onDismiss={() => {
            setCheckoutOrder(null);
            toast.info("Payment cancelled");
          }}
        />
      )}
    </div>
    </ProtectedRoute>
  );
}
