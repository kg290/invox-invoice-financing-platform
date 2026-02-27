"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Search,
  ChevronRight,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
  Users,
} from "lucide-react";
import api from "@/lib/api";
import { VendorResponse } from "@/lib/types";

function getStatusIcon(status: string) {
  switch (status) {
    case "verified":
      return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    case "rejected":
      return <AlertTriangle className="w-4 h-4 text-red-500" />;
    default:
      return <Clock className="w-4 h-4 text-yellow-500" />;
  }
}

function getCibilColor(score: number) {
  if (score >= 750) return "text-green-600";
  if (score >= 650) return "text-yellow-600";
  return "text-red-600";
}

export default function VendorList() {
  const [vendors, setVendors] = useState<VendorResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchVendors();
  }, []);

  const fetchVendors = async () => {
    try {
      const res = await api.get("/vendors/");
      setVendors(res.data);
    } catch {
      console.error("Failed to fetch vendors");
    } finally {
      setLoading(false);
    }
  };

  const filtered = vendors.filter(
    (v) =>
      v.full_name.toLowerCase().includes(search.toLowerCase()) ||
      v.business_name.toLowerCase().includes(search.toLowerCase()) ||
      v.gstin.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <ProtectedRoute>
    <div className="min-h-screen bg-gray-50 font-[family-name:var(--font-geist-sans)]">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">
                Invo<span className="text-blue-600">X</span>
              </span>
            </Link>
            <Link
              href="/vendor/register"
              className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              + New Vendor
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Registered Vendors</h1>
            <p className="text-sm text-gray-500 mt-1">
              {vendors.length} vendor{vendors.length !== 1 ? "s" : ""} registered
            </p>
          </div>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, business, or GSTIN..."
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 w-full sm:w-80 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">
              {search ? "No vendors match your search" : "No vendors registered yet"}
            </p>
            {!search && (
              <Link
                href="/vendor/register"
                className="inline-block mt-4 text-blue-600 hover:underline text-sm"
              >
                Register the first vendor →
              </Link>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 divide-y divide-gray-100">
            {filtered.map((v) => (
              <Link
                key={v.id}
                href={`/vendor/${v.id}`}
                className="flex items-center justify-between p-5 hover:bg-gray-50 transition-colors group"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center text-white font-bold text-lg flex-shrink-0">
                    {v.full_name.charAt(0)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-gray-900">
                        {v.full_name}
                      </h3>
                      {getStatusIcon(v.profile_status)}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {v.business_name} · {v.business_type}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      GSTIN: {v.gstin}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right hidden sm:block">
                    <p className="text-xs text-gray-500">CIBIL</p>
                    <p
                      className={`text-sm font-bold ${getCibilColor(
                        v.cibil_score
                      )}`}
                    >
                      {v.cibil_score}
                    </p>
                  </div>
                  <div className="text-right hidden sm:block">
                    <p className="text-xs text-gray-500">Turnover</p>
                    <p className="text-sm font-medium text-gray-900">
                      ₹{(v.annual_turnover / 100000).toFixed(1)}L
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-gray-500 transition-colors" />
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
