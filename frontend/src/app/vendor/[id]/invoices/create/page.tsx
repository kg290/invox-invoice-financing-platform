"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FileText, ArrowLeft, Plus, Trash2, Loader2, Check,
  AlertCircle,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import { INDIAN_STATES, GST_RATES, UNITS, InvoiceItem } from "@/lib/types";

const emptyItem: InvoiceItem = {
  description: "",
  hsn_sac_code: "",
  quantity: 1,
  unit: "NOS",
  unit_price: 0,
  discount_percent: 0,
  gst_rate: 18,
  cess_rate: 0,
};

function calcItem(item: InvoiceItem, supplyType: string) {
  const gross = item.quantity * item.unit_price;
  const disc = +(gross * item.discount_percent / 100).toFixed(2);
  const taxable = +(gross - disc).toFixed(2);
  const gstAmt = +(taxable * item.gst_rate / 100).toFixed(2);
  const cgst = supplyType === "intra_state" ? +(gstAmt / 2).toFixed(2) : 0;
  const sgst = supplyType === "intra_state" ? +(gstAmt / 2).toFixed(2) : 0;
  const igst = supplyType === "inter_state" ? gstAmt : 0;
  const cess = +(taxable * item.cess_rate / 100).toFixed(2);
  const total = +(taxable + cgst + sgst + igst + cess).toFixed(2);
  return { disc, taxable, cgst, sgst, igst, cess, total };
}

export default function CreateInvoicePage() {
  const params = useParams();
  const vendorId = params.id as string;
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    invoice_date: new Date().toISOString().slice(0, 10),
    due_date: "",
    supply_type: "intra_state",
    place_of_supply: "",
    reverse_charge: false,
    payment_status: "unpaid",
    buyer_name: "",
    buyer_gstin: "",
    buyer_address: "",
    buyer_city: "",
    buyer_state: "",
    buyer_pincode: "",
    buyer_phone: "",
    buyer_email: "",
    notes: "",
    terms: "Payment due within the specified due date. Late payments attract 18% p.a. interest.",
  });

  const [items, setItems] = useState<InvoiceItem[]>([{ ...emptyItem }]);
  const [sendEmail, setSendEmail] = useState(false);

  const updateForm = (field: string, value: string | boolean) =>
    setForm((f) => ({ ...f, [field]: value }));

  const updateItem = (idx: number, field: string, value: string | number) =>
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, [field]: value } : it)));

  const addItem = () => setItems((prev) => [...prev, { ...emptyItem }]);
  const removeItem = (idx: number) => {
    if (items.length <= 1) return;
    setItems((prev) => prev.filter((_, i) => i !== idx));
  };

  // Totals
  const totals = items.reduce(
    (acc, it) => {
      const c = calcItem(it, form.supply_type);
      return {
        subtotal: acc.subtotal + c.taxable,
        cgst: acc.cgst + c.cgst,
        sgst: acc.sgst + c.sgst,
        igst: acc.igst + c.igst,
        cess: acc.cess + c.cess,
        discount: acc.discount + c.disc,
      };
    },
    { subtotal: 0, cgst: 0, sgst: 0, igst: 0, cess: 0, discount: 0 }
  );
  const rawTotal = totals.subtotal + totals.cgst + totals.sgst + totals.igst + totals.cess;
  const roundOff = +(Math.round(rawTotal) - rawTotal).toFixed(2);
  const grandTotal = +(rawTotal + roundOff).toFixed(2);

  const onSubmit = async () => {
    if (!form.buyer_name || !form.place_of_supply || !form.due_date) {
      toast.error("Fill all required fields"); return;
    }
    if (items.some((it) => !it.description || !it.hsn_sac_code || it.unit_price <= 0)) {
      toast.error("Fill all item details with valid prices"); return;
    }

    setSubmitting(true);
    try {
      const payload = {
        ...form,
        buyer_gstin: form.buyer_gstin || null,
        buyer_phone: form.buyer_phone || null,
        buyer_email: form.buyer_email || null,
        notes: form.notes || null,
        terms: form.terms || null,
        items: items.map((it) => ({
          ...it,
          quantity: Number(it.quantity),
          unit_price: Number(it.unit_price),
          discount_percent: Number(it.discount_percent),
          gst_rate: Number(it.gst_rate),
          cess_rate: Number(it.cess_rate),
        })),
      };
      const res = await api.post(`/invoices/vendor/${vendorId}`, payload);
      toast.success(`Invoice ${res.data.invoice_number} created & recorded on blockchain!`);

      // Send email to client if checkbox was checked and buyer_email exists
      if (sendEmail && form.buyer_email) {
        try {
          await api.post(`/invoices/${res.data.id}/send-email`, { email: form.buyer_email });
          toast.success(`Invoice sent to ${form.buyer_email}`);
        } catch {
          toast.error("Invoice created but email sending failed");
        }
      }

      router.push(`/vendor/${vendorId}/invoices/${res.data.id}`);
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, "Failed to create invoice"));
    }
    setSubmitting(false);
  };

  const inputCls = "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none";
  const labelCls = "block text-xs font-medium text-gray-600 mb-1";
  const selectCls = "w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 bg-white focus:ring-2 focus:ring-blue-500 outline-none";

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-14">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">Invo<span className="text-blue-600">X</span></span>
          </Link>
          <Link href={`/vendor/${vendorId}/invoices`} className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> Invoices
          </Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <h1 className="text-xl font-bold text-gray-900 mb-6">Create GST Invoice</h1>

        {/* ── Invoice Details ── */}
        <div className="bg-white rounded-xl border p-5 mb-5">
          <h2 className="text-sm font-semibold text-gray-800 mb-4">Invoice Details</h2>
          <div className="grid sm:grid-cols-4 gap-4">
            <div>
              <label className={labelCls}>Invoice Date *</label>
              <input type="date" value={form.invoice_date} onChange={(e) => updateForm("invoice_date", e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Due Date *</label>
              <input type="date" value={form.due_date} onChange={(e) => updateForm("due_date", e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Supply Type *</label>
              <select value={form.supply_type} onChange={(e) => updateForm("supply_type", e.target.value)} className={selectCls}>
                <option value="intra_state">Intra-State (CGST+SGST)</option>
                <option value="inter_state">Inter-State (IGST)</option>
              </select>
            </div>
            <div>
              <label className={labelCls}>Place of Supply *</label>
              <select value={form.place_of_supply} onChange={(e) => updateForm("place_of_supply", e.target.value)} className={selectCls}>
                <option value="">Select State</option>
                {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-3">
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" checked={form.reverse_charge} onChange={(e) => updateForm("reverse_charge", e.target.checked)} className="rounded" />
              Reverse Charge Applicable
            </label>
          </div>

          {/* Payment Status */}
          <div className="mt-4">
            <label className={labelCls}>Payment Status *</label>
            <div className="flex gap-3 mt-1">
              <button
                type="button"
                onClick={() => updateForm("payment_status", "unpaid")}
                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  form.payment_status === "unpaid"
                    ? "bg-red-50 border-red-300 text-red-700 ring-2 ring-red-200"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                Unpaid
              </button>
              <button
                type="button"
                onClick={() => updateForm("payment_status", "paid")}
                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  form.payment_status === "paid"
                    ? "bg-green-50 border-green-300 text-green-700 ring-2 ring-green-200"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                Paid
              </button>
            </div>
            <p className="text-[11px] text-gray-400 mt-1">Only unpaid invoices can be listed on the financing marketplace</p>
          </div>
        </div>

        {/* ── Buyer Details ── */}
        <div className="bg-white rounded-xl border p-5 mb-5">
          <h2 className="text-sm font-semibold text-gray-800 mb-4">Buyer Details</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="sm:col-span-2 lg:col-span-1">
              <label className={labelCls}>Buyer Name *</label>
              <input value={form.buyer_name} onChange={(e) => updateForm("buyer_name", e.target.value)} className={inputCls} placeholder="Business/person name" />
            </div>
            <div>
              <label className={labelCls}>Buyer GSTIN</label>
              <input value={form.buyer_gstin} onChange={(e) => updateForm("buyer_gstin", e.target.value.toUpperCase())} className={inputCls} placeholder="Optional for B2C" maxLength={15} />
            </div>
            <div>
              <label className={labelCls}>Phone</label>
              <input value={form.buyer_phone} onChange={(e) => updateForm("buyer_phone", e.target.value)} className={inputCls} placeholder="Optional" />
            </div>
            <div>
              <label className={labelCls}>Email</label>
              <input type="email" value={form.buyer_email} onChange={(e) => updateForm("buyer_email", e.target.value)} className={inputCls} placeholder="client@email.com (optional)" />
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <label className={labelCls}>Address *</label>
              <input value={form.buyer_address} onChange={(e) => updateForm("buyer_address", e.target.value)} className={inputCls} placeholder="Full address" />
            </div>
            <div>
              <label className={labelCls}>City *</label>
              <input value={form.buyer_city} onChange={(e) => updateForm("buyer_city", e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>State *</label>
              <select value={form.buyer_state} onChange={(e) => updateForm("buyer_state", e.target.value)} className={selectCls}>
                <option value="">Select State</option>
                {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Pincode *</label>
              <input value={form.buyer_pincode} onChange={(e) => updateForm("buyer_pincode", e.target.value)} className={inputCls} maxLength={6} />
            </div>
          </div>
          {form.buyer_email && (
            <div className="mt-3">
              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input type="checkbox" checked={sendEmail} onChange={(e) => setSendEmail(e.target.checked)} className="rounded" />
                Send invoice to client via email after creation
              </label>
              <p className="text-[11px] text-gray-400 mt-1 ml-6">The invoice PDF will be emailed to {form.buyer_email}</p>
            </div>
          )}
        </div>

        {/* ── Line Items ── */}
        <div className="bg-white rounded-xl border p-5 mb-5">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-sm font-semibold text-gray-800">Line Items</h2>
            <button onClick={addItem} className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 font-medium">
              <Plus className="w-4 h-4" /> Add Item
            </button>
          </div>

          <div className="space-y-4">
            {items.map((item, idx) => {
              const c = calcItem(item, form.supply_type);
              return (
                <div key={idx} className="border rounded-lg p-4 bg-gray-50">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-semibold text-gray-500">Item #{idx + 1}</span>
                    {items.length > 1 && (
                      <button onClick={() => removeItem(idx)} className="text-red-500 hover:text-red-700"><Trash2 className="w-4 h-4" /></button>
                    )}
                  </div>
                  <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    <div className="sm:col-span-2">
                      <label className={labelCls}>Description *</label>
                      <input value={item.description} onChange={(e) => updateItem(idx, "description", e.target.value)} className={inputCls} placeholder="Product / Service" />
                    </div>
                    <div>
                      <label className={labelCls}>HSN/SAC Code *</label>
                      <input value={item.hsn_sac_code} onChange={(e) => updateItem(idx, "hsn_sac_code", e.target.value)} className={inputCls} placeholder="e.g. 8471" maxLength={8} />
                    </div>
                    <div>
                      <label className={labelCls}>Unit</label>
                      <select value={item.unit} onChange={(e) => updateItem(idx, "unit", e.target.value)} className={selectCls}>
                        {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className={labelCls}>Quantity *</label>
                      <input type="number" min={0.01} step="any" value={item.quantity} onChange={(e) => updateItem(idx, "quantity", Number(e.target.value))} className={inputCls} />
                    </div>
                    <div>
                      <label className={labelCls}>Unit Price (₹) *</label>
                      <input type="number" min={0} step="any" value={item.unit_price} onChange={(e) => updateItem(idx, "unit_price", Number(e.target.value))} className={inputCls} />
                    </div>
                    <div>
                      <label className={labelCls}>Discount %</label>
                      <input type="number" min={0} max={100} step="any" value={item.discount_percent} onChange={(e) => updateItem(idx, "discount_percent", Number(e.target.value))} className={inputCls} />
                    </div>
                    <div>
                      <label className={labelCls}>GST Rate %</label>
                      <select value={item.gst_rate} onChange={(e) => updateItem(idx, "gst_rate", Number(e.target.value))} className={selectCls}>
                        {GST_RATES.map((r) => <option key={r} value={r}>{r}%</option>)}
                      </select>
                    </div>
                  </div>
                  {/* Calculated preview */}
                  <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500 border-t pt-2">
                    <span>Taxable: <strong className="text-gray-800">₹{c.taxable.toLocaleString("en-IN")}</strong></span>
                    {form.supply_type === "intra_state" ? (
                      <>
                        <span>CGST: ₹{c.cgst.toLocaleString("en-IN")}</span>
                        <span>SGST: ₹{c.sgst.toLocaleString("en-IN")}</span>
                      </>
                    ) : (
                      <span>IGST: ₹{c.igst.toLocaleString("en-IN")}</span>
                    )}
                    {c.cess > 0 && <span>Cess: ₹{c.cess.toLocaleString("en-IN")}</span>}
                    <span>Total: <strong className="text-gray-900">₹{c.total.toLocaleString("en-IN")}</strong></span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Summary ── */}
        <div className="bg-white rounded-xl border p-5 mb-5">
          <h2 className="text-sm font-semibold text-gray-800 mb-3">Invoice Summary</h2>
          <div className="max-w-sm ml-auto space-y-1.5 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Sub Total</span><span>₹{totals.subtotal.toLocaleString("en-IN")}</span></div>
            {totals.discount > 0 && <div className="flex justify-between text-red-600"><span>Discount</span><span>-₹{totals.discount.toLocaleString("en-IN")}</span></div>}
            {form.supply_type === "intra_state" ? (
              <>
                <div className="flex justify-between"><span className="text-gray-500">CGST</span><span>₹{totals.cgst.toLocaleString("en-IN")}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">SGST</span><span>₹{totals.sgst.toLocaleString("en-IN")}</span></div>
              </>
            ) : (
              <div className="flex justify-between"><span className="text-gray-500">IGST</span><span>₹{totals.igst.toLocaleString("en-IN")}</span></div>
            )}
            {totals.cess > 0 && <div className="flex justify-between"><span className="text-gray-500">Cess</span><span>₹{totals.cess.toLocaleString("en-IN")}</span></div>}
            {roundOff !== 0 && <div className="flex justify-between text-gray-400"><span>Round Off</span><span>{roundOff > 0 ? "+" : ""}₹{roundOff}</span></div>}
            <div className="flex justify-between font-bold text-lg border-t pt-2 mt-2">
              <span>Grand Total</span><span>₹{grandTotal.toLocaleString("en-IN")}</span>
            </div>
          </div>
        </div>

        {/* ── Notes & Terms ── */}
        <div className="bg-white rounded-xl border p-5 mb-5 grid sm:grid-cols-2 gap-4">
          <div>
            <label className={labelCls}>Notes</label>
            <textarea value={form.notes} onChange={(e) => updateForm("notes", e.target.value)} className={inputCls} rows={3} placeholder="Internal notes..." />
          </div>
          <div>
            <label className={labelCls}>Terms & Conditions</label>
            <textarea value={form.terms} onChange={(e) => updateForm("terms", e.target.value)} className={inputCls} rows={3} />
          </div>
        </div>

        {/* ── Blockchain Notice ── */}
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-indigo-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-indigo-800">
            <strong>Blockchain Secured:</strong> Once created, this invoice will be hashed and recorded on the InvoX blockchain.
            The hash ensures immutability — any tampering will be detectable. The invoice can then be listed on the financing marketplace.
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end">
          <button onClick={onSubmit} disabled={submitting}
            className="inline-flex items-center gap-2 px-8 py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700 disabled:opacity-60 transition-colors">
            {submitting ? <><Loader2 className="w-5 h-5 animate-spin" /> Creating...</> : <><Check className="w-5 h-5" /> Create Invoice</>}
          </button>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
