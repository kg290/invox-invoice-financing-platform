"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, Loader2, IndianRupee, CreditCard, CheckCircle, Clock,
  AlertTriangle, ArrowLeft, Receipt, Wallet, ChevronDown, ChevronUp,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import InvoXPayCheckout, { type OrderData } from "@/components/InvoXPayCheckout";

interface Installment {
  id: number;
  installment_number: number;
  due_date: string;
  principal_amount: number;
  interest_amount: number;
  total_amount: number;
  status: string;
  paid_date: string | null;
  paid_amount: number | null;
}

interface RepaymentListing {
  listing_id: number;
  invoice_number: string;
  buyer_name: string;
  listing_status: string;
  funded_amount: number;
  interest_rate: number;
  total_due: number;
  total_paid: number;
  remaining: number;
  installments: Installment[];
}

export default function VendorRepayments() {
  const params = useParams();
  const vendorId = params.id as string;
  const [listings, setListings] = useState<RepaymentListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [paymentOrder, setPaymentOrder] = useState<OrderData | null>(null);
  const [activeInstallmentId, setActiveInstallmentId] = useState<number | null>(null);

  const fetchRepayments = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/marketplace/vendor-repayments/${vendorId}`);
      setListings(r.data);
      // Auto-expand first listing
      if (r.data.length > 0) {
        setExpanded({ [r.data[0].listing_id]: true });
      }
    } catch (err) {
      toast.error(getErrorMessage(err, "Failed to load repayments"));
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchRepayments();
  }, [vendorId]);

  const handlePay = async (listingId: number, installmentId: number) => {
    setPaying(installmentId);
    setActiveInstallmentId(installmentId);
    try {
      const r = await api.post("/payments/create-repayment-order", {
        listing_id: listingId,
        installment_id: installmentId,
      });
      setPaymentOrder(r.data);
    } catch (err) {
      toast.error(getErrorMessage(err, "Failed to create payment order"));
      setPaying(null);
      setActiveInstallmentId(null);
    }
  };

  const handlePaymentSuccess = () => {
    toast.success("Payment successful! Installment marked as paid.");
    setPaymentOrder(null);
    setPaying(null);
    setActiveInstallmentId(null);
    fetchRepayments();
  };

  const handlePaymentDismiss = () => {
    setPaymentOrder(null);
    setPaying(null);
    setActiveInstallmentId(null);
  };

  const toggleExpand = (listingId: number) => {
    setExpanded((prev) => ({ ...prev, [listingId]: !prev[listingId] }));
  };

  // Summary stats
  const totalDue = listings.reduce((acc, l) => acc + l.total_due, 0);
  const totalPaid = listings.reduce((acc, l) => acc + l.total_paid, 0);
  const totalRemaining = listings.reduce((acc, l) => acc + l.remaining, 0);
  const overdueCount = listings.reduce((acc, l) =>
    acc + l.installments.filter((i) => i.status === "pending" && new Date(i.due_date) < new Date()).length
  , 0);

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-[#f8f9fc]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">Invo<span className="text-indigo-600">X</span></span>
          </Link>
          <nav className="hidden sm:flex items-center gap-1">
            {[
              { label: "Dashboard", href: `/vendor/${vendorId}/dashboard` },
              { label: "Invoices", href: `/vendor/${vendorId}/invoices` },
              { label: "Repayments", href: `/vendor/${vendorId}/repayments`, active: true },
              { label: "Marketplace", href: "/marketplace" },
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
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Back + Title */}
        <div>
          <Link href={`/vendor/${vendorId}/dashboard`}
            className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3">
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Repayments</h1>
          <p className="text-sm text-gray-500 mt-1">Manage your loan repayments and track payment history</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <Loader2 className="w-10 h-10 text-indigo-600 animate-spin mx-auto mb-3" />
              <p className="text-sm text-gray-500">Loading repayments...</p>
            </div>
          </div>
        ) : listings.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
            <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <CreditCard className="w-8 h-8 text-gray-300" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">No Repayments Yet</h3>
            <p className="text-sm text-gray-500 mb-4">Repayments will appear here once your invoices are funded on the marketplace.</p>
            <Link href="/marketplace"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700">
              Browse Marketplace
            </Link>
          </div>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-2xl border border-gray-100 p-5">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-9 h-9 bg-indigo-50 rounded-xl flex items-center justify-center">
                    <Wallet className="w-4 h-4 text-indigo-600" />
                  </div>
                </div>
                <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">Total Due</p>
                <p className="text-xl font-bold text-gray-900 mt-0.5">₹{totalDue.toLocaleString("en-IN")}</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-100 p-5">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-9 h-9 bg-emerald-50 rounded-xl flex items-center justify-center">
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                  </div>
                </div>
                <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">Total Paid</p>
                <p className="text-xl font-bold text-emerald-700 mt-0.5">₹{totalPaid.toLocaleString("en-IN")}</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-100 p-5">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-9 h-9 bg-amber-50 rounded-xl flex items-center justify-center">
                    <Clock className="w-4 h-4 text-amber-600" />
                  </div>
                </div>
                <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">Remaining</p>
                <p className="text-xl font-bold text-amber-700 mt-0.5">₹{totalRemaining.toLocaleString("en-IN")}</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-100 p-5">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-9 h-9 bg-red-50 rounded-xl flex items-center justify-center">
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                  </div>
                </div>
                <p className="text-[11px] text-gray-400 uppercase tracking-wider font-medium">Overdue</p>
                <p className="text-xl font-bold text-red-700 mt-0.5">{overdueCount} installment{overdueCount !== 1 ? "s" : ""}</p>
              </div>
            </div>

            {/* Repayment Listings */}
            <div className="space-y-4">
              {listings.map((listing) => {
                const paidCount = listing.installments.filter((i) => i.status === "paid").length;
                const progress = listing.installments.length > 0
                  ? Math.round((paidCount / listing.installments.length) * 100) : 0;
                const isExpanded = expanded[listing.listing_id];

                return (
                  <div key={listing.listing_id} className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
                    {/* Listing Header */}
                    <button onClick={() => toggleExpand(listing.listing_id)}
                      className="w-full p-5 flex items-center justify-between hover:bg-gray-50 transition-colors text-left">
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                          listing.listing_status === "settled" ? "bg-emerald-50" : "bg-indigo-50"
                        }`}>
                          <Receipt className={`w-6 h-6 ${
                            listing.listing_status === "settled" ? "text-emerald-600" : "text-indigo-600"
                          }`} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-bold text-gray-900">Invoice #{listing.invoice_number}</h3>
                            <span className={`px-2 py-0.5 rounded-lg text-[10px] font-semibold ${
                              listing.listing_status === "settled"
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-blue-50 text-blue-700"
                            }`}>
                              {listing.listing_status === "settled" ? "Settled" : "Active"}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {listing.buyer_name} · ₹{listing.funded_amount.toLocaleString("en-IN")} funded · {listing.interest_rate}% interest
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right hidden sm:block">
                          <p className="text-xs text-gray-400">Progress</p>
                          <div className="flex items-center gap-2 mt-1">
                            <div className="w-24 h-2 bg-gray-100 rounded-full">
                              <div className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-full transition-all"
                                style={{ width: `${progress}%` }} />
                            </div>
                            <span className="text-xs font-semibold text-gray-600">{paidCount}/{listing.installments.length}</span>
                          </div>
                        </div>
                        {isExpanded ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
                      </div>
                    </button>

                    {/* Installments Table */}
                    {isExpanded && (
                      <div className="border-t border-gray-100">
                        {/* Summary Bar */}
                        <div className="flex gap-4 px-5 py-3 bg-gray-50 text-xs">
                          <span className="text-gray-500">Total: <strong className="text-gray-700">₹{listing.total_due.toLocaleString("en-IN")}</strong></span>
                          <span className="text-gray-500">Paid: <strong className="text-emerald-600">₹{listing.total_paid.toLocaleString("en-IN")}</strong></span>
                          <span className="text-gray-500">Remaining: <strong className="text-amber-600">₹{listing.remaining.toLocaleString("en-IN")}</strong></span>
                        </div>

                        {/* Table */}
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="text-gray-400 uppercase tracking-wider border-b border-gray-100">
                                <th className="px-5 py-3 text-left font-medium">#</th>
                                <th className="px-5 py-3 text-left font-medium">Due Date</th>
                                <th className="px-5 py-3 text-right font-medium">Principal</th>
                                <th className="px-5 py-3 text-right font-medium">Interest</th>
                                <th className="px-5 py-3 text-right font-medium">Total</th>
                                <th className="px-5 py-3 text-center font-medium">Status</th>
                                <th className="px-5 py-3 text-center font-medium">Action</th>
                              </tr>
                            </thead>
                            <tbody>
                              {listing.installments.map((inst) => {
                                const isOverdue = inst.status === "pending" && new Date(inst.due_date) < new Date();
                                return (
                                  <tr key={inst.id} className={`border-b border-gray-50 ${
                                    isOverdue ? "bg-red-50/50" : ""
                                  }`}>
                                    <td className="px-5 py-3.5 font-semibold text-gray-700">{inst.installment_number}</td>
                                    <td className="px-5 py-3.5 text-gray-600">
                                      {new Date(inst.due_date).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
                                      {isOverdue && (
                                        <span className="ml-1.5 text-[9px] font-semibold text-red-600 bg-red-100 px-1.5 py-0.5 rounded">OVERDUE</span>
                                      )}
                                    </td>
                                    <td className="px-5 py-3.5 text-right text-gray-600">₹{inst.principal_amount.toLocaleString("en-IN")}</td>
                                    <td className="px-5 py-3.5 text-right text-gray-400">₹{inst.interest_amount.toLocaleString("en-IN")}</td>
                                    <td className="px-5 py-3.5 text-right font-semibold text-gray-900">₹{inst.total_amount.toLocaleString("en-IN")}</td>
                                    <td className="px-5 py-3.5 text-center">
                                      {inst.status === "paid" ? (
                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-lg text-[10px] font-semibold">
                                          <CheckCircle className="w-3 h-3" /> Paid
                                        </span>
                                      ) : (
                                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-semibold ${
                                          isOverdue ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"
                                        }`}>
                                          {isOverdue ? <AlertTriangle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                                          {isOverdue ? "Overdue" : "Pending"}
                                        </span>
                                      )}
                                    </td>
                                    <td className="px-5 py-3.5 text-center">
                                      {inst.status !== "paid" && (
                                        <button
                                          onClick={() => handlePay(listing.listing_id, inst.id)}
                                          disabled={paying === inst.id}
                                          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-[11px] font-semibold transition-all active:scale-[0.97] disabled:opacity-60 ${
                                            isOverdue
                                              ? "bg-red-600 text-white hover:bg-red-700"
                                              : "bg-indigo-600 text-white hover:bg-indigo-700"
                                          }`}
                                        >
                                          {paying === inst.id ? (
                                            <Loader2 className="w-3 h-3 animate-spin" />
                                          ) : (
                                            <IndianRupee className="w-3 h-3" />
                                          )}
                                          {paying === inst.id ? "Paying..." : "Pay Now"}
                                        </button>
                                      )}
                                      {inst.status === "paid" && inst.paid_date && (
                                        <span className="text-[10px] text-gray-400">
                                          {new Date(inst.paid_date).toLocaleDateString("en-IN")}
                                        </span>
                                      )}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>

    {/* InvoX Pay Gateway Modal */}
    {paymentOrder && (
      <InvoXPayCheckout
        orderData={paymentOrder}
        onSuccess={handlePaymentSuccess}
        onDismiss={handlePaymentDismiss}
      />
    )}
    </ProtectedRoute>
  );
}
