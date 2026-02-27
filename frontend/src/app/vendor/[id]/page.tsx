"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  User,
  Building2,
  Receipt,
  Wallet,
  UserCheck,
  ArrowLeft,
  Shield,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Upload,
  Loader2,
  Fingerprint,
} from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { VendorDetailResponse } from "@/lib/types";

function getRiskLabel(score: number | null) {
  if (score === null) return { label: "Not Scored", color: "text-gray-500", bg: "bg-gray-100" };
  if (score >= 70) return { label: "Low Risk", color: "text-green-700", bg: "bg-green-100" };
  if (score >= 40) return { label: "Medium Risk", color: "text-yellow-700", bg: "bg-yellow-100" };
  return { label: "High Risk", color: "text-red-700", bg: "bg-red-100" };
}

function getStatusBadge(status: string) {
  switch (status) {
    case "verified":
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
          <CheckCircle2 className="w-3 h-3" /> Verified
        </span>
      );
    case "rejected":
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
          <AlertTriangle className="w-3 h-3" /> Rejected
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
          <Clock className="w-3 h-3" /> Pending Review
        </span>
      );
  }
}

function formatCurrency(val: number | null | undefined) {
  if (val == null) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(val);
}

const DOC_TYPES = [
  { key: "business_pan_doc", label: "Business PAN Card" },
  { key: "business_aadhaar_doc", label: "Business Aadhaar Card" },
  { key: "electricity_bill_doc", label: "Electricity Bill" },
  { key: "bank_statement_doc", label: "Bank Statement (6 months)" },
  { key: "registration_certificate_doc", label: "Registration Certificate" },
  { key: "gst_certificate_doc", label: "GST Certificate" },
];

export default function VendorDetail() {
  const params = useParams();
  const vendorId = params.id as string;
  const [vendor, setVendor] = useState<VendorDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState<string | null>(null);

  useEffect(() => {
    fetchVendor();
  }, []);

  const fetchVendor = async () => {
    try {
      const res = await api.get(`/vendors/${vendorId}`);
      setVendor(res.data);
    } catch {
      toast.error("Failed to load vendor details");
    } finally {
      setLoading(false);
    }
  };

  const handleDocUpload = async (docType: string, file: File) => {
    setUploading(docType);
    const formData = new FormData();
    formData.append("file", file);
    try {
      await api.post(`/vendors/${vendorId}/upload/${docType}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Document uploaded successfully!");
      fetchVendor();
    } catch {
      toast.error("Failed to upload document");
    } finally {
      setUploading(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!vendor) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <AlertTriangle className="w-12 h-12 text-red-500" />
        <p className="text-gray-600">Vendor not found</p>
        <Link href="/" className="text-blue-600 hover:underline">
          Go back home
        </Link>
      </div>
    );
  }

  const risk = getRiskLabel(vendor.risk_score);

  const InfoItem = ({
    label,
    value,
  }: {
    label: string;
    value: string | number | null | undefined;
  }) => (
    <div>
      <dt className="text-xs text-gray-500 mb-0.5">{label}</dt>
      <dd className="text-sm font-medium text-gray-900">
        {value || "—"}
      </dd>
    </div>
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
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Link
          href="/vendor/list"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back to vendors
        </Link>

        {/* Profile Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center text-white text-2xl font-bold">
                {vendor.full_name.charAt(0)}
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {vendor.full_name}
                </h1>
                <p className="text-gray-500">{vendor.business_name}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {getStatusBadge(vendor.profile_status)}
              <span
                className={`inline-flex items-center gap-1 px-3 py-1 ${risk.bg} ${risk.color} text-xs font-medium rounded-full`}
              >
                <Shield className="w-3 h-3" />
                {risk.label} ({vendor.risk_score ?? "N/A"}/100)
              </span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid sm:grid-cols-5 gap-3 mb-6">
          <Link href={`/vendor/${vendorId}/verify`}
            className="flex items-center gap-3 bg-white border rounded-xl p-4 hover:shadow-md transition-shadow group">
            <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center group-hover:bg-green-100 transition-colors">
              <UserCheck className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Verify</p>
              <p className="text-xs text-gray-500">Check genuineness</p>
            </div>
          </Link>
          <Link href="/kyc"
            className="flex items-center gap-3 bg-white border rounded-xl p-4 hover:shadow-md transition-shadow group">
            <div className="w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
              <Fingerprint className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">KYC</p>
              <p className="text-xs text-gray-500">Identity check</p>
            </div>
          </Link>
          <Link href={`/vendor/${vendorId}/invoices`}
            className="flex items-center gap-3 bg-white border rounded-xl p-4 hover:shadow-md transition-shadow group">
            <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center group-hover:bg-blue-100 transition-colors">
              <Receipt className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Invoices</p>
              <p className="text-xs text-gray-500">Billing system</p>
            </div>
          </Link>
          <Link href={`/vendor/${vendorId}/invoices/create`}
            className="flex items-center gap-3 bg-white border rounded-xl p-4 hover:shadow-md transition-shadow group">
            <div className="w-10 h-10 bg-purple-50 rounded-lg flex items-center justify-center group-hover:bg-purple-100 transition-colors">
              <FileText className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">New Invoice</p>
              <p className="text-xs text-gray-500">Create GST bill</p>
            </div>
          </Link>
          <Link href="/marketplace"
            className="flex items-center gap-3 bg-white border rounded-xl p-4 hover:shadow-md transition-shadow group">
            <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center group-hover:bg-amber-100 transition-colors">
              <Wallet className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Marketplace</p>
              <p className="text-xs text-gray-500">Invoice financing</p>
            </div>
          </Link>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Personal Details */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-blue-600" /> Personal Details
            </h2>
            <dl className="grid grid-cols-2 gap-4">
              <InfoItem label="Full Name" value={vendor.full_name} />
              <InfoItem label="Date of Birth" value={vendor.date_of_birth} />
              <InfoItem label="Phone" value={vendor.phone} />
              <InfoItem label="Email" value={vendor.email} />
              <InfoItem label="PAN" value={vendor.personal_pan} />
              <InfoItem
                label="Aadhaar"
                value={`XXXX XXXX ${vendor.personal_aadhaar.slice(-4)}`}
              />
              <div className="col-span-2">
                <InfoItem
                  label="Address"
                  value={`${vendor.address}, ${vendor.city}, ${vendor.state} - ${vendor.pincode}`}
                />
              </div>
            </dl>
          </div>

          {/* Business Details */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-600" /> Business Details
            </h2>
            <dl className="grid grid-cols-2 gap-4">
              <InfoItem label="Business Name" value={vendor.business_name} />
              <InfoItem label="Type" value={vendor.business_type} />
              <InfoItem label="Category" value={vendor.business_category} />
              <InfoItem
                label="Est. Year"
                value={vendor.year_of_establishment}
              />
              <InfoItem
                label="Registration No."
                value={vendor.business_registration_number}
              />
              <InfoItem
                label="UDYAM No."
                value={vendor.udyam_registration_number}
              />
              <InfoItem
                label="Employees"
                value={vendor.number_of_employees}
              />
              <div className="col-span-2">
                <InfoItem
                  label="Business Address"
                  value={`${vendor.business_address}, ${vendor.business_city}, ${vendor.business_state} - ${vendor.business_pincode}`}
                />
              </div>
            </dl>
          </div>

          {/* GST Details */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Receipt className="w-5 h-5 text-blue-600" /> GST Details
            </h2>
            <dl className="grid grid-cols-2 gap-4">
              <InfoItem label="GSTIN" value={vendor.gstin} />
              <InfoItem
                label="Registration Date"
                value={vendor.gst_registration_date}
              />
              <InfoItem
                label="Filing Frequency"
                value={vendor.gst_filing_frequency}
              />
              <InfoItem
                label="Total Filings"
                value={vendor.total_gst_filings}
              />
              <InfoItem
                label="Compliance Status"
                value={vendor.gst_compliance_status}
              />
            </dl>
          </div>

          {/* Financial Details */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Wallet className="w-5 h-5 text-blue-600" /> Financial Details
            </h2>
            <dl className="grid grid-cols-2 gap-4">
              <InfoItem label="CIBIL Score" value={vendor.cibil_score} />
              <InfoItem
                label="Annual Turnover"
                value={formatCurrency(vendor.annual_turnover)}
              />
              <InfoItem
                label="Monthly Revenue"
                value={formatCurrency(vendor.monthly_revenue)}
              />
              <InfoItem
                label="Business Assets"
                value={formatCurrency(vendor.business_assets_value)}
              />
              <InfoItem
                label="Existing Liabilities"
                value={formatCurrency(vendor.existing_liabilities)}
              />
              <InfoItem label="Bank" value={vendor.bank_name} />
              <InfoItem label="Account No." value={`XXXX${vendor.bank_account_number.slice(-4)}`} />
              <InfoItem label="IFSC" value={vendor.bank_ifsc} />
              <InfoItem label="Branch" value={vendor.bank_branch} />
            </dl>
          </div>

          {/* Nominee Details */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-blue-600" /> Nominee Details
            </h2>
            <dl className="grid grid-cols-2 gap-4">
              <InfoItem label="Name" value={vendor.nominee_name} />
              <InfoItem
                label="Relationship"
                value={vendor.nominee_relationship}
              />
              <InfoItem label="Phone" value={vendor.nominee_phone} />
              <InfoItem
                label="Aadhaar"
                value={
                  vendor.nominee_aadhaar
                    ? `XXXX XXXX ${vendor.nominee_aadhaar.slice(-4)}`
                    : null
                }
              />
            </dl>
          </div>

          {/* Document Uploads */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-blue-600" /> Documents
            </h2>
            <div className="space-y-3">
              {DOC_TYPES.map((doc) => {
                const uploaded =
                  vendor[doc.key as keyof VendorDetailResponse];
                return (
                  <div
                    key={doc.key}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      {uploaded ? (
                        <CheckCircle2 className="w-4 h-4 text-green-500" />
                      ) : (
                        <Clock className="w-4 h-4 text-gray-400" />
                      )}
                      <span className="text-sm text-gray-700">
                        {doc.label}
                      </span>
                    </div>
                    {uploaded ? (
                      <span className="text-xs text-green-600 font-medium">
                        Uploaded
                      </span>
                    ) : (
                      <label className="cursor-pointer">
                        <input
                          type="file"
                          className="hidden"
                          accept=".pdf,.jpg,.jpeg,.png"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleDocUpload(doc.key, file);
                          }}
                        />
                        <span className="text-xs text-blue-600 font-medium hover:underline flex items-center gap-1">
                          {uploading === doc.key ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Upload className="w-3 h-3" />
                          )}
                          Upload
                        </span>
                      </label>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
    </ProtectedRoute>
  );
}
