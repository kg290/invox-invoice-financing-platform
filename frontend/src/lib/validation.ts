import { z } from "zod";

/**
 * Simplified vendor registration schema — only 4 fields.
 * Everything else is auto-fetched from the Government Citizen Database.
 */
export const vendorQuickSchema = z.object({
  full_name: z.string().min(2, "Name must be at least 2 characters").max(255),
  personal_pan: z
    .string()
    .length(10, "PAN must be exactly 10 characters")
    .regex(/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/, "Invalid PAN format (e.g., ABCDE1234F)"),
  personal_aadhaar: z
    .string()
    .length(12, "Aadhaar must be exactly 12 digits")
    .regex(/^\d{12}$/, "Aadhaar must contain only digits"),
  gstin: z
    .string()
    .length(15, "GSTIN must be exactly 15 characters")
    .regex(
      /^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$/,
      "Invalid GSTIN format (e.g., 22ABCDE1234F1Z5)"
    ),
});

export type VendorQuickSchemaType = z.infer<typeof vendorQuickSchema>;

export const vendorSchema = z.object({
  // Personal Details
  full_name: z.string().min(2, "Name must be at least 2 characters").max(255),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  phone: z
    .string()
    .min(10, "Phone must be at least 10 digits")
    .max(15)
    .regex(/^\d{10,13}$/, "Enter a valid phone number (digits only)"),
  email: z.string().email("Enter a valid email address"),
  personal_pan: z
    .string()
    .length(10, "PAN must be exactly 10 characters")
    .regex(/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/, "Invalid PAN format (e.g., ABCDE1234F)"),
  personal_aadhaar: z
    .string()
    .length(12, "Aadhaar must be exactly 12 digits")
    .regex(/^\d{12}$/, "Aadhaar must contain only digits"),
  address: z.string().min(5, "Address must be at least 5 characters"),
  city: z.string().min(2, "City is required"),
  state: z.string().min(1, "State is required"),
  pincode: z
    .string()
    .length(6, "Pincode must be 6 digits")
    .regex(/^\d{6}$/, "Pincode must be digits only"),

  // Business Details
  business_name: z.string().min(2, "Business name is required").max(255),
  business_type: z.string().min(1, "Business type is required"),
  business_category: z.string().min(1, "Business category is required"),
  business_registration_number: z.string().optional().or(z.literal("")),
  udyam_registration_number: z
    .string()
    .optional()
    .or(z.literal(""))
    .refine(
      (val) => !val || /^UDYAM-[A-Z]{2}-\d{2}-\d{7}$/.test(val),
      "Invalid UDYAM format (e.g., UDYAM-MH-00-0000000)"
    ),
  year_of_establishment: z.coerce
    .number()
    .min(1900, "Year must be after 1900")
    .max(2026, "Year cannot be in the future"),
  number_of_employees: z.coerce.number().min(0).optional().or(z.literal("")),
  business_address: z.string().min(5, "Business address is required"),
  business_city: z.string().min(2, "Business city is required"),
  business_state: z.string().min(1, "Business state is required"),
  business_pincode: z
    .string()
    .length(6, "Pincode must be 6 digits")
    .regex(/^\d{6}$/, "Pincode must be digits only"),

  // GST Details — only GSTIN is required; rest auto-filled from govt API
  gstin: z
    .string()
    .length(15, "GSTIN must be exactly 15 characters")
    .regex(
      /^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$/,
      "Invalid GSTIN format (e.g., 22ABCDE1234F1Z5)"
    ),
  gst_registration_date: z.string().optional().or(z.literal("")),
  gst_filing_frequency: z.string().optional().or(z.literal("")),
  total_gst_filings: z.coerce.number().min(0).optional().or(z.literal("")),
  gst_compliance_status: z.string().optional().or(z.literal("")),

  // Financial Details — CIBIL score is AUTO-FETCHED, not user-entered
  cibil_score: z.coerce.number().min(300).max(900).optional().or(z.literal("")),
  annual_turnover: z.coerce.number().min(0, "Must be 0 or more"),
  monthly_revenue: z.coerce.number().min(0).optional().or(z.literal("")),
  business_assets_value: z.coerce.number().min(0, "Must be 0 or more"),
  existing_liabilities: z.coerce.number().min(0).optional().or(z.literal("")),
  bank_account_number: z
    .string()
    .min(8, "Account number must be at least 8 digits")
    .max(20),
  bank_name: z.string().min(1, "Bank name is required"),
  bank_ifsc: z
    .string()
    .length(11, "IFSC must be exactly 11 characters")
    .regex(/^[A-Z]{4}0[A-Z0-9]{6}$/, "Invalid IFSC format (e.g., SBIN0001234)"),
  bank_branch: z.string().optional().or(z.literal("")),

  // Nominee Details
  nominee_name: z.string().min(2, "Nominee name is required"),
  nominee_relationship: z.string().min(1, "Relationship is required"),
  nominee_phone: z
    .string()
    .min(10, "Phone must be at least 10 digits")
    .max(15)
    .regex(/^\d{10,13}$/, "Enter a valid phone number"),
  nominee_aadhaar: z
    .string()
    .optional()
    .or(z.literal(""))
    .refine(
      (val) => !val || /^\d{12}$/.test(val),
      "Aadhaar must be exactly 12 digits"
    ),
});

export type VendorSchemaType = z.infer<typeof vendorSchema>;
