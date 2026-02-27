"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, ArrowLeft, Loader2, ShieldCheck, Store, AlertCircle,
  CheckCircle, Calendar, Hash, IndianRupee, Copy, Download, Mail, Send,
  ImagePlus, X,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import { InvoiceResponse } from "@/lib/types";

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  sent: "bg-blue-100 text-blue-700",
  paid: "bg-green-100 text-green-700",
  overdue: "bg-red-100 text-red-700",
  cancelled: "bg-red-50 text-red-500",
  partially_paid: "bg-yellow-100 text-yellow-700",
};

export default function InvoiceDetailPage() {
  const params = useParams();
  const vendorId = params.id as string;
  const invoiceId = params.invoiceId as string;
  const [inv, setInv] = useState<InvoiceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [listing, setListing] = useState(false);
  const [showListModal, setShowListModal] = useState(false);
  const [listForm, setListForm] = useState({ listing_title: "", listing_description: "", max_interest_rate: 12, repayment_period_days: 90 });
  const [listImages, setListImages] = useState<File[]>([]);
  const [downloading, setDownloading] = useState(false);
  const [emailing, setEmailing] = useState(false);

  const fetchInvoice = () => {
    api.get(`/invoices/${invoiceId}`).then((r) => { setInv(r.data); setLoading(false); }).catch(() => setLoading(false));
  };
  useEffect(fetchInvoice, [invoiceId]);

  const listOnMarketplace = async () => {
    if (listForm.max_interest_rate <= 0 || listForm.repayment_period_days <= 0) {
      toast.error("Invalid interest rate or repayment period");
      return;
    }
    setListing(true);
    try {
      const formData = new FormData();
      formData.append("listing_title", listForm.listing_title);
      formData.append("listing_description", listForm.listing_description);
      formData.append("max_interest_rate", String(listForm.max_interest_rate));
      formData.append("repayment_period_days", String(listForm.repayment_period_days));
      listImages.forEach((file) => formData.append("images", file));
      await api.post(`/marketplace/list/${invoiceId}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Invoice listed on the marketplace!");
      setShowListModal(false);
      setListImages([]);
      fetchInvoice();
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to list"));
    }
    setListing(false);
  };

  const updateStatus = async (status: string) => {
    try {
      await api.patch(`/invoices/${invoiceId}/status`, { status });
      toast.success(`Status updated to ${status}`);
      fetchInvoice();
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to update status"));
    }
  };

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const res = await api.get(`/invoices/${invoiceId}/pdf`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${inv?.invoice_number || "invoice"}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("PDF downloaded!");
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to download PDF"));
    }
    setDownloading(false);
  };

  const sendEmail = async () => {
    if (!inv?.buyer_email) {
      toast.error("No buyer email address on this invoice");
      return;
    }
    setEmailing(true);
    try {
      await api.post(`/invoices/${invoiceId}/send-email`, { email: inv.buyer_email });
      toast.success(`Invoice sent to ${inv.buyer_email}`);
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to send email"));
    }
    setEmailing(false);
  };

  const copyHash = () => {
    if (inv?.blockchain_hash) {
      navigator.clipboard.writeText(inv.blockchain_hash);
      toast.success("Hash copied!");
    }
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /></div>
  );
  if (!inv) return (
    <div className="min-h-screen flex items-center justify-center flex-col gap-2">
      <AlertCircle className="w-10 h-10 text-red-400" />
      <p className="text-gray-600">Invoice not found</p>
    </div>
  );

  const isIntraState = inv.supply_type === "intra_state";

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-14">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">Invo<span className="text-blue-600">X</span></span>
          </Link>
          <Link href={`/vendor/${vendorId}/invoices`} className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> All Invoices
          </Link>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">
        {/* ── Header ── */}
        <div className="bg-white rounded-xl border p-5">
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                {inv.invoice_number}
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium uppercase ${statusColors[inv.invoice_status] || "bg-gray-100"}`}>
                  {inv.invoice_status.replace("_", " ")}
                </span>
              </h1>
              <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-500">
                <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> {new Date(inv.invoice_date).toLocaleDateString("en-IN")}</span>
                <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Due: {new Date(inv.due_date).toLocaleDateString("en-IN")}</span>
                <span className="flex items-center gap-1"><Hash className="w-3.5 h-3.5" /> {isIntraState ? "Intra-State" : "Inter-State"}</span>
                {inv.reverse_charge && <span className="text-amber-600 font-medium">Reverse Charge</span>}
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">Grand Total</p>
              <p className="text-2xl font-bold text-gray-900 flex items-center gap-1 justify-end">
                <IndianRupee className="w-5 h-5" /> {inv.grand_total.toLocaleString("en-IN")}
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t">
            {/* Payment status badge */}
            <span className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
              inv.payment_status === "paid" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
            }`}>
              {inv.payment_status === "paid" ? "Paid" : "Unpaid"}
            </span>

            {/* PDF Download */}
            <button onClick={downloadPdf} disabled={downloading}
              className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 inline-flex items-center gap-1">
              {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} Download PDF
            </button>

            {/* Email to client */}
            {inv.buyer_email && (
              <button onClick={sendEmail} disabled={emailing}
                className="px-4 py-2 bg-blue-50 text-blue-700 text-sm rounded-lg hover:bg-blue-100 inline-flex items-center gap-1">
                {emailing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Email to Client
              </button>
            )}

            {inv.invoice_status === "draft" && (
              <button onClick={() => updateStatus("issued")} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">Mark as Issued</button>
            )}
            {(inv.invoice_status === "issued" || inv.invoice_status === "overdue") && inv.payment_status !== "paid" && (
              <button onClick={() => updateStatus("paid")} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700">Mark as Paid</button>
            )}
            {!inv.is_listed && inv.invoice_status !== "cancelled" && inv.payment_status !== "paid" && (
              <button onClick={() => setShowListModal(true)}
                className="px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 inline-flex items-center gap-1">
                <Store className="w-4 h-4" /> List on Marketplace
              </button>
            )}
            {inv.is_listed && (
              <span className="px-4 py-2 bg-purple-50 text-purple-700 text-sm rounded-lg font-medium inline-flex items-center gap-1">
                <Store className="w-4 h-4" /> Listed on Marketplace
              </span>
            )}
          </div>
        </div>

        {/* ── Buyer Details ── */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-800 mb-3">Buyer Details</h2>
          <div className="grid sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
            <div><span className="text-gray-500">Name:</span> <span className="font-medium">{inv.buyer_name}</span></div>
            {inv.buyer_gstin && <div><span className="text-gray-500">GSTIN:</span> <span className="font-mono text-xs">{inv.buyer_gstin}</span></div>}
            <div className="sm:col-span-2"><span className="text-gray-500">Address:</span> {inv.buyer_address}, {inv.buyer_city}, {inv.buyer_state} - {inv.buyer_pincode}</div>
            <div><span className="text-gray-500">Place of Supply:</span> {inv.place_of_supply}</div>
          </div>
        </div>

        {/* ── Line Items ── */}
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="p-5 pb-3">
            <h2 className="text-sm font-semibold text-gray-800">Line Items</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">#</th>
                  <th className="px-4 py-2 text-left">Description</th>
                  <th className="px-4 py-2 text-left">HSN/SAC</th>
                  <th className="px-4 py-2 text-right">Qty</th>
                  <th className="px-4 py-2 text-right">Rate (₹)</th>
                  <th className="px-4 py-2 text-right">Taxable</th>
                  {isIntraState ? (
                    <>
                      <th className="px-4 py-2 text-right">CGST</th>
                      <th className="px-4 py-2 text-right">SGST</th>
                    </>
                  ) : (
                    <th className="px-4 py-2 text-right">IGST</th>
                  )}
                  <th className="px-4 py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {inv.items.map((it, idx) => (
                  <tr key={it.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500">{idx + 1}</td>
                    <td className="px-4 py-3 font-medium">{it.description}</td>
                    <td className="px-4 py-3 font-mono text-xs">{it.hsn_sac_code}</td>
                    <td className="px-4 py-3 text-right">{it.quantity} {it.unit}</td>
                    <td className="px-4 py-3 text-right">{it.unit_price.toLocaleString("en-IN")}</td>
                    <td className="px-4 py-3 text-right">{it.taxable_value.toLocaleString("en-IN")}</td>
                    {isIntraState ? (
                      <>
                        <td className="px-4 py-3 text-right text-xs">{it.cgst_amount.toLocaleString("en-IN")} <span className="text-gray-400">({it.gst_rate / 2}%)</span></td>
                        <td className="px-4 py-3 text-right text-xs">{it.sgst_amount.toLocaleString("en-IN")} <span className="text-gray-400">({it.gst_rate / 2}%)</span></td>
                      </>
                    ) : (
                      <td className="px-4 py-3 text-right text-xs">{it.igst_amount.toLocaleString("en-IN")} <span className="text-gray-400">({it.gst_rate}%)</span></td>
                    )}
                    <td className="px-4 py-3 text-right font-semibold">{it.total_amount.toLocaleString("en-IN")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Summary ── */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-800 mb-3">Tax Summary</h2>
          <div className="max-w-xs ml-auto space-y-1.5 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Sub Total</span><span>₹{inv.subtotal.toLocaleString("en-IN")}</span></div>
            {inv.total_discount > 0 && <div className="flex justify-between text-red-600"><span>Discount</span><span>-₹{inv.total_discount.toLocaleString("en-IN")}</span></div>}
            {isIntraState ? (
              <>
                <div className="flex justify-between"><span className="text-gray-500">CGST</span><span>₹{inv.total_cgst.toLocaleString("en-IN")}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">SGST</span><span>₹{inv.total_sgst.toLocaleString("en-IN")}</span></div>
              </>
            ) : (
              <div className="flex justify-between"><span className="text-gray-500">IGST</span><span>₹{inv.total_igst.toLocaleString("en-IN")}</span></div>
            )}
            {inv.total_cess > 0 && <div className="flex justify-between"><span className="text-gray-500">Cess</span><span>₹{inv.total_cess.toLocaleString("en-IN")}</span></div>}
            {inv.round_off !== 0 && <div className="flex justify-between text-gray-400"><span>Round Off</span><span>{inv.round_off > 0 ? "+" : ""}₹{inv.round_off}</span></div>}
            <div className="flex justify-between font-bold text-lg border-t pt-2 mt-2">
              <span>Grand Total</span><span>₹{inv.grand_total.toLocaleString("en-IN")}</span>
            </div>
          </div>
        </div>

        {/* ── Blockchain Proof ── */}
        {inv.blockchain_hash && (
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <ShieldCheck className="w-5 h-5 text-indigo-600" />
              <h2 className="text-sm font-semibold text-indigo-800">Blockchain Proof</h2>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-indigo-600 font-medium w-24">Block Hash:</span>
                <code className="font-mono bg-white px-2 py-1 rounded border border-indigo-200 text-indigo-900 break-all flex-1">{inv.blockchain_hash}</code>
                <button onClick={copyHash} className="text-indigo-600 hover:text-indigo-800"><Copy className="w-4 h-4" /></button>
              </div>
              {inv.block_index && (
                <div className="flex items-center gap-2">
                  <span className="text-indigo-600 font-medium w-24">Block ID:</span>
                  <span className="text-indigo-900 font-mono">#{inv.block_index}</span>
                </div>
              )}
              <div className="flex items-center gap-1 mt-2 text-indigo-700">
                <CheckCircle className="w-3.5 h-3.5" /> This invoice is immutably recorded on the InvoX blockchain
              </div>
            </div>
          </div>
        )}

        {/* ── Notes/Terms ── */}
        {(inv.notes || inv.terms) && (
          <div className="bg-white rounded-xl border p-5 grid sm:grid-cols-2 gap-4 text-sm">
            {inv.notes && <div><p className="text-xs font-semibold text-gray-500 mb-1">Notes</p><p className="text-gray-700">{inv.notes}</p></div>}
            {inv.terms && <div><p className="text-xs font-semibold text-gray-500 mb-1">Terms & Conditions</p><p className="text-gray-700">{inv.terms}</p></div>}
          </div>
        )}
      </div>

      {/* ── Marketplace Listing Modal ── */}
      {showListModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold text-gray-900 mb-1 flex items-center gap-2">
              <Store className="w-5 h-5 text-purple-600" /> List on Marketplace
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              Invoice {inv.invoice_number} · ₹{inv.grand_total.toLocaleString("en-IN")}
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Listing Title *
                </label>
                <input type="text" maxLength={255}
                  value={listForm.listing_title}
                  onChange={(e) => setListForm({ ...listForm, listing_title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="e.g. Invoice financing for textile order" />
                <p className="text-[11px] text-gray-400 mt-1">A short title that lenders will see on the marketplace</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Description about your business
                </label>
                <textarea maxLength={2000} rows={3}
                  value={listForm.listing_description}
                  onChange={(e) => setListForm({ ...listForm, listing_description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-purple-500 outline-none resize-none"
                  placeholder="Tell lenders about your business, the invoice, and why you need financing..." />
                <p className="text-[11px] text-gray-400 mt-1">Helps lenders decide to fund your invoice</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Maximum Interest Rate (% p.a.) *
                </label>
                <input type="number" step="0.1" min="0.1" max="36"
                  value={listForm.max_interest_rate}
                  onChange={(e) => setListForm({ ...listForm, max_interest_rate: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="e.g. 12" />
                <p className="text-[11px] text-gray-400 mt-1">The maximum annual interest rate you are willing to pay a lender</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Repayment Period (days) *
                </label>
                <input type="number" min="7" max="365"
                  value={listForm.repayment_period_days}
                  onChange={(e) => setListForm({ ...listForm, repayment_period_days: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-purple-500 outline-none"
                  placeholder="e.g. 90" />
                <p className="text-[11px] text-gray-400 mt-1">Number of days you need to repay the funded amount</p>
              </div>
              {/* ── Optional Business Images ── */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Business Photos (optional)
                </label>
                <label className="flex items-center justify-center gap-2 w-full px-3 py-3 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-purple-400 hover:bg-purple-50/30 transition-colors">
                  <ImagePlus className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-500">Click to upload photos</span>
                  <input type="file" multiple accept="image/*" className="hidden"
                    onChange={(e) => {
                      if (e.target.files) setListImages((prev) => [...prev, ...Array.from(e.target.files!)]);
                    }} />
                </label>
                {listImages.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {listImages.map((file, i) => (
                      <div key={i} className="relative group">
                        <img src={URL.createObjectURL(file)} alt="" className="w-16 h-16 object-cover rounded-lg border" />
                        <button type="button" onClick={() => setListImages((prev) => prev.filter((_, idx) => idx !== i))}
                          className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-[11px] text-gray-400 mt-1">Upload photos of your business for lenders to see on the marketplace</p>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowListModal(false)}
                className="flex-1 px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
              <button onClick={listOnMarketplace} disabled={listing}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-60 inline-flex items-center justify-center gap-1">
                {listing ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />} List Invoice
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
    </ProtectedRoute>
  );
}
