"use client";

import { useState, useEffect } from "react";
import {
  X, CreditCard, Smartphone, Building2, Lock, Shield,
  CheckCircle, Loader2, ArrowLeft, ChevronRight, AlertCircle,
  Zap, IndianRupee, Eye, EyeOff,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";

/* ── Types ── */
export interface OrderData {
  order_id: string;
  amount: number;
  amount_paise: number;
  currency: string;
  description: string;
  payer_name?: string;
  payer_email?: string;
  gateway?: string;
}

interface InvoXPayProps {
  orderData: OrderData;
  onSuccess: (result: Record<string, unknown>) => void;
  onFailure?: (error: string) => void;
  onDismiss?: () => void;
}

type PaymentMethod = "card" | "upi" | "netbanking";
type CheckoutStep = "method" | "details" | "processing" | "success" | "failure";

const BANKS = [
  { code: "SBI", name: "State Bank of India", icon: "🏦" },
  { code: "HDFC", name: "HDFC Bank", icon: "🏛️" },
  { code: "ICICI", name: "ICICI Bank", icon: "🏢" },
  { code: "AXIS", name: "Axis Bank", icon: "🏬" },
  { code: "KOTAK", name: "Kotak Mahindra Bank", icon: "🏪" },
  { code: "BOB", name: "Bank of Baroda", icon: "🏣" },
  { code: "PNB", name: "Punjab National Bank", icon: "🏤" },
  { code: "YES", name: "Yes Bank", icon: "🏫" },
];

const formatCardNumber = (value: string) => {
  const v = value.replace(/\D/g, "").slice(0, 16);
  const parts = [];
  for (let i = 0; i < v.length; i += 4) parts.push(v.slice(i, i + 4));
  return parts.join(" ");
};

const formatExpiry = (value: string) => {
  const v = value.replace(/\D/g, "").slice(0, 4);
  if (v.length >= 3) return `${v.slice(0, 2)}/${v.slice(2)}`;
  return v;
};

export default function InvoXPayCheckout({ orderData, onSuccess, onFailure, onDismiss }: InvoXPayProps) {
  const [step, setStep] = useState<CheckoutStep>("method");
  const [method, setMethod] = useState<PaymentMethod>("card");
  const [error, setError] = useState("");
  const [showCvv, setShowCvv] = useState(false);

  // Card fields
  const [cardNumber, setCardNumber] = useState("");
  const [cardExpiry, setCardExpiry] = useState("");
  const [cardCvv, setCardCvv] = useState("");
  const [cardHolder, setCardHolder] = useState(orderData.payer_name || "");

  // UPI
  const [upiId, setUpiId] = useState("");

  // Net banking
  const [bankCode, setBankCode] = useState("");

  // Processing animation
  const [processingStep, setProcessingStep] = useState(0);
  const processingSteps = [
    "Encrypting payment data...",
    "Connecting to banking network...",
    "Validating credentials...",
    "Processing transaction...",
    "Confirming payment...",
  ];

  // Success data
  const [successData, setSuccessData] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (step === "processing") {
      let i = 0;
      const interval = setInterval(() => {
        i++;
        if (i < processingSteps.length) {
          setProcessingStep(i);
        } else {
          clearInterval(interval);
        }
      }, 600);
      return () => clearInterval(interval);
    }
  }, [step]);

  const processPayment = async () => {
    setError("");
    setStep("processing");
    setProcessingStep(0);

    try {
      // Step 1: Process payment on backend
      const processRes = await api.post("/payments/process", {
        order_id: orderData.order_id,
        payment_method: method,
        ...(method === "card" && {
          card_number: cardNumber.replace(/\s/g, ""),
          card_expiry: cardExpiry,
          card_cvv: cardCvv,
          card_holder: cardHolder,
        }),
        ...(method === "upi" && { upi_id: upiId }),
        ...(method === "netbanking" && { bank_code: bankCode }),
      });

      // Simulate processing delay for realism
      await new Promise((r) => setTimeout(r, 2500));

      // Step 2: Verify payment
      const verifyRes = await api.post("/payments/verify", {
        order_id: processRes.data.order_id,
        payment_id: processRes.data.payment_id,
        signature: processRes.data.signature,
      });

      setSuccessData(verifyRes.data);
      setStep("success");

      // Auto-callback after showing success
      setTimeout(() => {
        onSuccess(verifyRes.data);
      }, 2000);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      const msg = getErrorMessage(err, "Payment processing failed");
      setError(msg);
      setStep("failure");
    }
  };

  const handleSubmit = () => {
    setError("");
    if (method === "card") {
      const raw = cardNumber.replace(/\s/g, "");
      if (raw.length < 13) { setError("Enter a valid card number"); return; }
      if (!cardExpiry || cardExpiry.length < 5) { setError("Enter card expiry (MM/YY)"); return; }
      if (!cardCvv || cardCvv.length < 3) { setError("Enter CVV"); return; }
      if (!cardHolder.trim()) { setError("Enter cardholder name"); return; }
    } else if (method === "upi") {
      if (!upiId || !upiId.includes("@")) { setError("Enter valid UPI ID (e.g., name@upi)"); return; }
    } else if (method === "netbanking") {
      if (!bankCode) { setError("Select a bank"); return; }
    }
    processPayment();
  };

  const getCardType = (num: string) => {
    const n = num.replace(/\s/g, "");
    if (n.startsWith("4")) return { name: "Visa", color: "text-blue-600", bg: "bg-blue-50" };
    if (n.startsWith("5") || n.startsWith("2")) return { name: "Mastercard", color: "text-red-600", bg: "bg-red-50" };
    if (n.startsWith("6")) return { name: "RuPay", color: "text-green-600", bg: "bg-green-50" };
    if (n.startsWith("3")) return { name: "Amex", color: "text-purple-600", bg: "bg-purple-50" };
    return null;
  };

  const cardType = getCardType(cardNumber);

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[100] p-4" onClick={onDismiss}>
      <div className="bg-white rounded-3xl w-full max-w-[440px] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300" onClick={(e) => e.stopPropagation()}>

        {/* ── Header ── */}
        <div className="bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 px-6 py-5 text-white relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(255,255,255,0.1),transparent)]" />
          <div className="relative">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <Zap className="w-4 h-4" />
                </div>
                <span className="text-lg font-bold tracking-tight">InvoX Pay</span>
              </div>
              <button onClick={onDismiss} className="p-1.5 hover:bg-white/20 rounded-lg transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-[11px] font-medium uppercase tracking-wider">Amount</p>
                <p className="text-2xl font-bold mt-0.5">
                  <span className="text-white/60 text-lg">₹</span>
                  {orderData.amount.toLocaleString("en-IN")}
                </p>
              </div>
              <div className="text-right">
                <p className="text-white/70 text-[10px]">{orderData.description}</p>
                <div className="flex items-center gap-1 mt-1 text-[10px] text-white/50">
                  <Lock className="w-3 h-3" />
                  <span>256-bit SSL encrypted</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Body ── */}
        <div className="p-6">

          {/* METHOD SELECT */}
          {(step === "method" || step === "details") && (
            <>
              {step === "method" && (
                <div className="space-y-2.5 mb-5">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Select Payment Method</p>

                  {/* Card */}
                  <button onClick={() => { setMethod("card"); setStep("details"); }}
                    className="w-full flex items-center gap-4 p-4 border-2 border-gray-100 rounded-2xl hover:border-indigo-300 hover:bg-indigo-50/50 transition-all group">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200/50">
                      <CreditCard className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-sm font-bold text-gray-900">Credit / Debit Card</p>
                      <p className="text-[11px] text-gray-500">Visa, Mastercard, RuPay, Amex</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-indigo-500 transition-colors" />
                  </button>

                  {/* UPI */}
                  <button onClick={() => { setMethod("upi"); setStep("details"); }}
                    className="w-full flex items-center gap-4 p-4 border-2 border-gray-100 rounded-2xl hover:border-emerald-300 hover:bg-emerald-50/50 transition-all group">
                    <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-green-600 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-200/50">
                      <Smartphone className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-sm font-bold text-gray-900">UPI</p>
                      <p className="text-[11px] text-gray-500">Google Pay, PhonePe, Paytm, BHIM</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-emerald-500 transition-colors" />
                  </button>

                  {/* Net Banking */}
                  <button onClick={() => { setMethod("netbanking"); setStep("details"); }}
                    className="w-full flex items-center gap-4 p-4 border-2 border-gray-100 rounded-2xl hover:border-amber-300 hover:bg-amber-50/50 transition-all group">
                    <div className="w-12 h-12 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center shadow-lg shadow-amber-200/50">
                      <Building2 className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-sm font-bold text-gray-900">Net Banking</p>
                      <p className="text-[11px] text-gray-500">All major Indian banks supported</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-amber-500 transition-colors" />
                  </button>
                </div>
              )}

              {/* DETAILS FORM */}
              {step === "details" && (
                <div>
                  <button onClick={() => setStep("method")} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 mb-4 transition-colors">
                    <ArrowLeft className="w-3.5 h-3.5" /> Change payment method
                  </button>

                  {/* Card Form */}
                  {method === "card" && (
                    <div className="space-y-3.5">
                      <div>
                        <label className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider mb-1.5 block">Card Number</label>
                        <div className="relative">
                          <input
                            type="text" value={cardNumber}
                            onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                            placeholder="4111 1111 1111 1111"
                            maxLength={19}
                            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 font-mono tracking-wider focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all pr-20"
                          />
                          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
                            {cardType && (
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${cardType.bg} ${cardType.color}`}>{cardType.name}</span>
                            )}
                            <CreditCard className="w-4 h-4 text-gray-300" />
                          </div>
                        </div>
                      </div>

                      <div>
                        <label className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider mb-1.5 block">Card Holder</label>
                        <input
                          type="text" value={cardHolder}
                          onChange={(e) => setCardHolder(e.target.value.toUpperCase())}
                          placeholder="JOHN DOE"
                          className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 uppercase tracking-wide focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider mb-1.5 block">Expiry</label>
                          <input
                            type="text" value={cardExpiry}
                            onChange={(e) => setCardExpiry(formatExpiry(e.target.value))}
                            placeholder="MM/YY"
                            maxLength={5}
                            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 font-mono tracking-widest text-center focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                          />
                        </div>
                        <div>
                          <label className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider mb-1.5 block">CVV</label>
                          <div className="relative">
                            <input
                              type={showCvv ? "text" : "password"} value={cardCvv}
                              onChange={(e) => setCardCvv(e.target.value.replace(/\D/g, "").slice(0, 4))}
                              placeholder="•••"
                              maxLength={4}
                              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 font-mono tracking-widest text-center focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all pr-10"
                            />
                            <button type="button" onClick={() => setShowCvv(!showCvv)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                              {showCvv ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                          </div>
                        </div>
                      </div>

                      <div className="bg-blue-50 border border-blue-200 rounded-xl p-2.5 flex items-center gap-2 text-[10px] text-blue-700">
                        <Shield className="w-4 h-4 flex-shrink-0" />
                        <span>Test card: <span className="font-mono font-bold">4111 1111 1111 1111</span> · Any future expiry · CVV: 123</span>
                      </div>
                    </div>
                  )}

                  {/* UPI Form */}
                  {method === "upi" && (
                    <div className="space-y-3.5">
                      <div>
                        <label className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider mb-1.5 block">UPI ID</label>
                        <input
                          type="text" value={upiId}
                          onChange={(e) => setUpiId(e.target.value.toLowerCase())}
                          placeholder="yourname@upi"
                          className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 outline-none transition-all"
                        />
                      </div>
                      <div className="grid grid-cols-4 gap-2">
                        {["@ybl", "@axl", "@okicici", "@paytm"].map((suffix) => (
                          <button key={suffix} onClick={() => setUpiId((upiId.split("@")[0] || "name") + suffix)}
                            className="px-2 py-2 bg-gray-100 rounded-lg text-[10px] font-medium text-gray-600 hover:bg-emerald-100 hover:text-emerald-700 transition-all">
                            {suffix}
                          </button>
                        ))}
                      </div>
                      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-2.5 flex items-center gap-2 text-[10px] text-emerald-700">
                        <Smartphone className="w-4 h-4 flex-shrink-0" />
                        <span>Test UPI: <span className="font-mono font-bold">test@ybl</span> or any valid UPI format</span>
                      </div>
                    </div>
                  )}

                  {/* Net Banking */}
                  {method === "netbanking" && (
                    <div className="space-y-2">
                      <p className="text-[11px] font-semibold text-gray-600 uppercase tracking-wider mb-2">Select Your Bank</p>
                      <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                        {BANKS.map((bank) => (
                          <button key={bank.code} onClick={() => setBankCode(bank.code)}
                            className={`flex items-center gap-2.5 p-3 rounded-xl border-2 transition-all text-left ${
                              bankCode === bank.code
                                ? "border-amber-400 bg-amber-50 ring-2 ring-amber-100"
                                : "border-gray-100 hover:border-amber-200 hover:bg-amber-50/30"
                            }`}>
                            <span className="text-lg">{bank.icon}</span>
                            <div>
                              <p className="text-[11px] font-bold text-gray-900">{bank.code}</p>
                              <p className="text-[9px] text-gray-500 leading-tight">{bank.name}</p>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Error display */}
                  {error && (
                    <div className="mt-3 bg-red-50 border border-red-200 rounded-xl p-3 flex items-center gap-2 text-xs text-red-700">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                      {error}
                    </div>
                  )}

                  {/* Pay Button */}
                  <button onClick={handleSubmit}
                    className="w-full mt-5 py-3.5 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-xl text-sm font-bold hover:shadow-xl hover:shadow-indigo-200 transition-all active:scale-[0.98] flex items-center justify-center gap-2">
                    <Lock className="w-4 h-4" />
                    Pay ₹{orderData.amount.toLocaleString("en-IN")}
                  </button>
                </div>
              )}
            </>
          )}

          {/* PROCESSING */}
          {step === "processing" && (
            <div className="py-8 text-center">
              <div className="relative inline-block mb-6">
                <div className="w-20 h-20 border-4 border-indigo-100 rounded-full" />
                <div className="w-20 h-20 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin absolute inset-0" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <IndianRupee className="w-8 h-8 text-indigo-600" />
                </div>
              </div>
              <p className="text-sm font-bold text-gray-900 mb-3">Processing Payment</p>
              <div className="space-y-1.5 max-w-xs mx-auto">
                {processingSteps.map((s, i) => (
                  <div key={i} className={`flex items-center gap-2 text-xs transition-all duration-300 ${
                    i < processingStep ? "text-emerald-600" : i === processingStep ? "text-indigo-600 font-medium" : "text-gray-300"
                  }`}>
                    {i < processingStep ? (
                      <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
                    ) : i === processingStep ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin flex-shrink-0" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-gray-200 flex-shrink-0" />
                    )}
                    <span>{s}</span>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-gray-400 mt-4">Do not close this window or press back</p>
            </div>
          )}

          {/* SUCCESS */}
          {step === "success" && (
            <div className="py-8 text-center">
              <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4 animate-in zoom-in-50 duration-500">
                <CheckCircle className="w-10 h-10 text-emerald-600" />
              </div>
              <p className="text-lg font-bold text-gray-900 mb-1">Payment Successful!</p>
              <p className="text-sm text-gray-500 mb-4">₹{orderData.amount.toLocaleString("en-IN")} paid via {method === "card" ? "Card" : method === "upi" ? "UPI" : "Net Banking"}</p>
              <div className="bg-gray-50 rounded-xl p-3 text-left max-w-xs mx-auto space-y-1.5 text-[11px]">
                <div className="flex justify-between"><span className="text-gray-500">Transaction ID</span><span className="font-mono font-bold text-gray-900">{String(successData.payment_id || "").slice(0, 20)}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Amount</span><span className="font-bold text-gray-900">₹{orderData.amount.toLocaleString("en-IN")}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Status</span><span className="font-bold text-emerald-600">Confirmed</span></div>
              </div>
              <p className="text-[10px] text-gray-400 mt-4 flex items-center justify-center gap-1">
                <Shield className="w-3 h-3" /> Secured by InvoX Pay · Blockchain verified
              </p>
            </div>
          )}

          {/* FAILURE */}
          {step === "failure" && (
            <div className="py-8 text-center">
              <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-10 h-10 text-red-500" />
              </div>
              <p className="text-lg font-bold text-gray-900 mb-1">Payment Failed</p>
              <p className="text-sm text-red-500 mb-5">{error || "Something went wrong"}</p>
              <div className="flex gap-3">
                <button onClick={() => { setError(""); setStep("details"); }}
                  className="flex-1 py-3 border-2 border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-all">
                  Try Again
                </button>
                <button onClick={() => onFailure?.(error || "Payment failed")}
                  className="flex-1 py-3 bg-gray-900 text-white rounded-xl text-sm font-semibold hover:bg-gray-800 transition-all">
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="px-6 pb-4 pt-2 border-t border-gray-100">
          <div className="flex items-center justify-center gap-3 text-[10px] text-gray-400">
            <div className="flex items-center gap-1">
              <Lock className="w-3 h-3" />
              <span>PCI DSS</span>
            </div>
            <span>•</span>
            <div className="flex items-center gap-1">
              <Shield className="w-3 h-3" />
              <span>256-bit SSL</span>
            </div>
            <span>•</span>
            <span className="font-semibold text-indigo-500">InvoX Pay</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Helper to create funding order ── */
export async function createFundingOrder(params: {
  listing_id: number;
  lender_id: number;
  funded_amount: number;
  offered_interest_rate: number;
}): Promise<OrderData> {
  const res = await api.post("/payments/create-funding-order", params);
  return res.data;
}

/* ── Helper to create repayment order ── */
export async function createRepaymentOrder(params: {
  listing_id: number;
  installment_id: number;
}): Promise<OrderData> {
  const res = await api.post("/payments/create-repayment-order", params);
  return res.data;
}

/* ── Helper to create pay-all-remaining order ── */
export async function createPayAllOrder(params: {
  listing_id: number;
}): Promise<OrderData> {
  const res = await api.post("/payments/create-pay-all-order", params);
  return res.data;
}

/* ── Helper to request refund ── */
export async function requestRefund(params: {
  listing_id: number;
  reason: string;
}): Promise<{ message: string; refund_amount: number; refund_payment_id: string; blockchain_hash: string }> {
  const res = await api.post("/payments/refund", params);
  return res.data;
}
