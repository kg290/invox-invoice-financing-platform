"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  Bot, Loader2, ArrowLeft, MessageSquare, CheckCircle, AlertCircle,
  Building2, Info, X, Clock, TrendingUp, Shield, Percent,
  IndianRupee, Users,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import { NegotiationChat, NegotiationChatMessage } from "@/lib/types";

export default function VendorNegotiationsPage() {
  const params = useParams();
  const vendorId = params.id as string;
  const [negotiations, setNegotiations] = useState<NegotiationChat[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChat, setSelectedChat] = useState<NegotiationChat | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.get(`/negotiate/vendor/${vendorId}`)
      .then((r) => setNegotiations(r.data || []))
      .catch((err) => toast.error(getErrorMessage(err, "Failed to load negotiations")))
      .finally(() => setLoading(false));
  }, [vendorId]);

  useEffect(() => {
    // Auto-scroll to bottom when chat changes
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [selectedChat]);

  const statusBadge = (status: string) => {
    const cfg: Record<string, { bg: string; text: string }> = {
      active: { bg: "bg-green-50 border-green-200", text: "text-green-700" },
      accepted: { bg: "bg-emerald-50 border-emerald-200", text: "text-emerald-700" },
      rejected: { bg: "bg-red-50 border-red-200", text: "text-red-700" },
      expired: { bg: "bg-gray-50 border-gray-200", text: "text-gray-500" },
    };
    const c = cfg[status] || cfg.expired;
    return (
      <span className={`text-[10px] font-bold px-2 py-0.5 border rounded-full ${c.bg} ${c.text}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  const activeCount = negotiations.filter(n => n.status === "active").length;
  const acceptedCount = negotiations.filter(n => n.status === "accepted").length;

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
    </div>
  );

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-purple-50/30">
        {/* Header */}
        <div className="bg-white border-b border-gray-100 sticky top-0 z-30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Link href={`/vendor/${vendorId}/dashboard`}
                  className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
                  <ArrowLeft className="w-5 h-5 text-gray-500" />
                </Link>
                <div>
                  <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                    <Bot className="w-6 h-6 text-purple-600" />
                    AI Negotiations
                  </h1>
                  <p className="text-xs text-gray-500 mt-0.5">
                    View all AI-powered negotiations on your invoices
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 text-xs bg-green-50 text-green-700 px-3 py-1.5 rounded-full border border-green-200">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  {activeCount} Active
                </div>
                <div className="flex items-center gap-1.5 text-xs bg-emerald-50 text-emerald-700 px-3 py-1.5 rounded-full border border-emerald-200">
                  <CheckCircle className="w-3 h-3" />
                  {acceptedCount} Accepted
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {negotiations.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
              <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h2 className="text-lg font-bold text-gray-900 mb-2">No Negotiations Yet</h2>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                When lenders start negotiating on your marketplace listings, the AI agent will handle it for you. All conversations will appear here.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Negotiations List */}
              <div className="lg:col-span-1 space-y-3">
                <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-2">
                  All Negotiations ({negotiations.length})
                </h2>
                {negotiations.map((neg) => (
                  <button
                    key={neg.session_id}
                    onClick={() => setSelectedChat(neg)}
                    className={`w-full text-left bg-white rounded-xl border p-4 hover:shadow-md transition-all ${
                      selectedChat?.session_id === neg.session_id
                        ? "border-purple-300 ring-2 ring-purple-100 shadow-md"
                        : "border-gray-100"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-indigo-500" />
                        <span className="text-sm font-bold text-gray-900">{neg.lender.name}</span>
                      </div>
                      {statusBadge(neg.status)}
                    </div>
                    {neg.invoice_number && (
                      <p className="text-[10px] text-gray-400 mb-1.5">Invoice #{neg.invoice_number}</p>
                    )}
                    <div className="flex items-center gap-3 text-[11px] text-gray-500">
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-3 h-3" />
                        {neg.messages.length} msgs
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        R{neg.current_round}/{neg.max_rounds}
                      </span>
                      <span className="flex items-center gap-1">
                        <IndianRupee className="w-3 h-3" />
                        {neg.invoice_amount?.toLocaleString("en-IN")}
                      </span>
                    </div>
                    {neg.final_rate && (
                      <div className="mt-2 text-xs bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-lg inline-flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        Final: {neg.final_rate}% · ₹{neg.final_amount?.toLocaleString("en-IN")}
                      </div>
                    )}
                  </button>
                ))}
              </div>

              {/* Chat View */}
              <div className="lg:col-span-2">
                {!selectedChat ? (
                  <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center h-[600px] flex flex-col items-center justify-center">
                    <MessageSquare className="w-12 h-12 text-gray-300 mb-4" />
                    <h3 className="text-lg font-bold text-gray-900 mb-2">Select a Negotiation</h3>
                    <p className="text-sm text-gray-500">Click on a negotiation from the list to view the full chat transcript</p>
                  </div>
                ) : (
                  <div className="bg-white rounded-2xl border border-gray-100 flex flex-col h-[600px] overflow-hidden">
                    {/* Chat Header */}
                    <div className="p-4 border-b border-gray-100 flex-shrink-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center">
                            <Bot className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <h3 className="text-sm font-bold text-gray-900">
                              {selectedChat.lender.name}
                              <span className="text-gray-400 font-normal ml-1.5 text-xs">
                                ({selectedChat.lender.organization || selectedChat.lender.type})
                              </span>
                            </h3>
                            <p className="text-[10px] text-gray-400">
                              Round {selectedChat.current_round}/{selectedChat.max_rounds} · Started {selectedChat.created_at ? new Date(selectedChat.created_at).toLocaleDateString("en-IN") : ""}
                            </p>
                          </div>
                        </div>
                        {statusBadge(selectedChat.status)}
                      </div>

                      {/* Context stats */}
                      <div className="flex gap-2 mt-3">
                        <div className="flex-1 bg-gray-50 rounded-lg px-2.5 py-1.5 text-center">
                          <p className="text-[8px] text-gray-400 uppercase">Amount</p>
                          <p className="text-[11px] font-bold text-gray-800">₹{selectedChat.invoice_amount?.toLocaleString("en-IN")}</p>
                        </div>
                        <div className="flex-1 bg-gray-50 rounded-lg px-2.5 py-1.5 text-center">
                          <p className="text-[8px] text-gray-400 uppercase">Fair Rate</p>
                          <p className="text-[11px] font-bold text-gray-800">{selectedChat.fair_market_rate}%</p>
                        </div>
                        <div className="flex-1 bg-gray-50 rounded-lg px-2.5 py-1.5 text-center">
                          <p className="text-[8px] text-gray-400 uppercase">Max Rate</p>
                          <p className="text-[11px] font-bold text-gray-800">{selectedChat.max_interest_rate}%</p>
                        </div>
                        <div className="flex-1 bg-gray-50 rounded-lg px-2.5 py-1.5 text-center">
                          <p className="text-[8px] text-gray-400 uppercase">Grade</p>
                          <p className="text-[11px] font-bold text-gray-800">{selectedChat.vendor_risk_grade}</p>
                        </div>
                        {selectedChat.final_rate && (
                          <div className="flex-1 bg-emerald-50 rounded-lg px-2.5 py-1.5 text-center">
                            <p className="text-[8px] text-emerald-500 uppercase">Final</p>
                            <p className="text-[11px] font-bold text-emerald-700">{selectedChat.final_rate}%</p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Chat Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50/50">
                      {selectedChat.messages.map((msg) => (
                        <div key={msg.id} className={`flex ${msg.sender === "lender" ? "justify-end" : "justify-start"}`}>
                          <div className={`max-w-[80%]`}>
                            <div className="flex items-end gap-2">
                              {msg.sender !== "lender" && (
                                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                                  msg.sender === "ai_agent" ? "bg-gradient-to-br from-violet-500 to-purple-600" : "bg-gray-300"
                                }`}>
                                  {msg.sender === "ai_agent" ? <Bot className="w-3.5 h-3.5 text-white" /> : <Info className="w-3.5 h-3.5 text-gray-500" />}
                                </div>
                              )}
                              <div className={`rounded-2xl px-3.5 py-2.5 ${
                                msg.sender === "lender"
                                  ? "bg-indigo-600 text-white rounded-br-md"
                                  : msg.sender === "ai_agent"
                                  ? "bg-white border border-gray-200 text-gray-800 rounded-bl-md shadow-sm"
                                  : "bg-gray-200 text-gray-600 rounded-bl-md"
                              }`}>
                                <p className="text-[12px] leading-relaxed whitespace-pre-wrap">{msg.message.replace(/\*\*/g, '')}</p>
                                {msg.offered_rate && (
                                  <div className={`flex gap-3 mt-1.5 pt-1.5 text-[9px] ${
                                    msg.sender === "lender" ? "border-t border-white/20 text-white/70" : "border-t border-gray-100 text-gray-400"
                                  }`}>
                                    <span>Rate: <span className="font-bold">{msg.offered_rate}%</span></span>
                                    {msg.offered_amount && <span>₹{msg.offered_amount.toLocaleString("en-IN")}</span>}
                                    {msg.offer_score && <span>Score: {msg.offer_score}/100</span>}
                                  </div>
                                )}
                              </div>
                              {msg.sender === "lender" && (
                                <div className="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                                  <Building2 className="w-3.5 h-3.5 text-indigo-600" />
                                </div>
                              )}
                            </div>
                            <p className={`text-[8px] text-gray-400 mt-0.5 ${msg.sender === "lender" ? "text-right mr-8" : "ml-8"}`}>
                              {msg.sender === "ai_agent" ? "AI Agent (You)" : msg.sender === "lender" ? selectedChat.lender.name : "System"}
                              {msg.created_at && ` · ${new Date(msg.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`}
                            </p>
                          </div>
                        </div>
                      ))}

                      {/* Deal status banners */}
                      {selectedChat.status === "accepted" && (
                        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-center">
                          <div className="flex items-center justify-center gap-2 mb-1">
                            <CheckCircle className="w-4 h-4 text-emerald-600" />
                            <span className="text-xs font-bold text-emerald-800">Deal Accepted</span>
                          </div>
                          <p className="text-[10px] text-emerald-600">
                            Rate: {selectedChat.final_rate}% · Amount: ₹{selectedChat.final_amount?.toLocaleString("en-IN")} · Score: {selectedChat.final_score}/100
                          </p>
                        </div>
                      )}
                      {selectedChat.status === "rejected" && (
                        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-center">
                          <div className="flex items-center justify-center gap-2 mb-1">
                            <AlertCircle className="w-4 h-4 text-red-600" />
                            <span className="text-xs font-bold text-red-800">No Agreement</span>
                          </div>
                          <p className="text-[10px] text-red-600">Negotiation ended without a deal</p>
                        </div>
                      )}
                      <div ref={chatEndRef} />
                    </div>

                    {/* Footer */}
                    <div className="p-3 border-t border-gray-100 flex-shrink-0 bg-white">
                      <p className="text-[10px] text-gray-400 text-center flex items-center justify-center gap-1.5">
                        <Shield className="w-3 h-3 text-purple-400" />
                        AI agent negotiated on your behalf · Read-only view
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
