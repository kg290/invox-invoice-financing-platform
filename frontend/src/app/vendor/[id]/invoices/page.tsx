"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  FileText, Plus, ArrowLeft, Loader2, Search, IndianRupee,
  ShieldCheck, Calendar, Tag,
} from "lucide-react";
import api from "@/lib/api";
import { InvoiceListItem } from "@/lib/types";

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  sent: "bg-blue-100 text-blue-700",
  paid: "bg-green-100 text-green-700",
  overdue: "bg-red-100 text-red-700",
  cancelled: "bg-red-50 text-red-500",
  partially_paid: "bg-yellow-100 text-yellow-700",
};

export default function InvoiceListPage() {
  const params = useParams();
  const vendorId = params.id as string;
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get(`/invoices/vendor/${vendorId}`).then((r) => {
      setInvoices(r.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [vendorId]);

  const filtered = invoices.filter(
    (inv) =>
      inv.invoice_number.toLowerCase().includes(search.toLowerCase()) ||
      inv.buyer_name.toLowerCase().includes(search.toLowerCase())
  );

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
          <div className="flex items-center gap-4">
            <Link href={`/vendor/${vendorId}`} className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1">
              <ArrowLeft className="w-4 h-4" /> Vendor
            </Link>
            <Link href={`/vendor/${vendorId}/invoices/create`}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
              <Plus className="w-4 h-4" /> New Invoice
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <h1 className="text-xl font-bold text-gray-900">Invoices</h1>
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="Search by number or buyer..." />
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /></div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No invoices found.</p>
            <Link href={`/vendor/${vendorId}/invoices/create`} className="text-blue-600 text-sm hover:underline mt-2 inline-block">
              Create your first invoice →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((inv) => (
              <Link key={inv.id} href={`/vendor/${vendorId}/invoices/${inv.id}`}
                className="block bg-white border rounded-xl p-4 hover:shadow-md transition-shadow">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileText className="w-5 h-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{inv.invoice_number}</p>
                      <p className="text-xs text-gray-500">{inv.buyer_name}</p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 sm:gap-5 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" /> {new Date(inv.invoice_date).toLocaleDateString("en-IN")}
                    </span>
                    <span className="flex items-center gap-1">
                      <IndianRupee className="w-3.5 h-3.5" />
                      <strong className="text-gray-900 text-sm">₹{inv.grand_total.toLocaleString("en-IN")}</strong>
                    </span>
                    <span className="flex items-center gap-1">
                      <Tag className="w-3.5 h-3.5" />
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium uppercase ${statusColors[inv.invoice_status] || "bg-gray-100 text-gray-600"}`}>
                        {inv.invoice_status.replace("_", " ")}
                      </span>
                    </span>
                    {inv.blockchain_hash && (
                      <span className="flex items-center gap-1 text-indigo-600" title="Blockchain secured">
                        <ShieldCheck className="w-3.5 h-3.5" /> Secured
                      </span>
                    )}
                    {inv.is_listed && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium uppercase bg-purple-100 text-purple-700">
                        Listed
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
    </ProtectedRoute>
  );
}
