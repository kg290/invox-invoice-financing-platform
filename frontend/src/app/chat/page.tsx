"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import {
  MessageSquare, Send, Loader2, ArrowLeft, Plus, Search,
  FileText, Users, X, Clock, CheckCheck, Bell,
} from "lucide-react";
import api, { getErrorMessage } from "@/lib/api";
import { ChatConversation, ChatMessage, ChatAvailableUser } from "@/lib/types";

export default function ChatPage() {
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [activeConv, setActiveConv] = useState<ChatConversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMsg, setNewMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [msgLoading, setMsgLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [showNewChat, setShowNewChat] = useState(false);
  const [availableUsers, setAvailableUsers] = useState<ChatAvailableUser[]>([]);
  const [userSearch, setUserSearch] = useState("");
  const [totalUnread, setTotalUnread] = useState(0);
  const [currentUser, setCurrentUser] = useState<{ id: number; role: string; vendor_id: number | null; lender_id: number | null } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load current user
  useEffect(() => {
    const stored = localStorage.getItem("invox_user");
    if (stored) setCurrentUser(JSON.parse(stored));
  }, []);

  // Fetch conversations
  const fetchConversations = useCallback(async () => {
    try {
      const r = await api.get("/chat/conversations");
      setConversations(r.data);
    } catch { /* ignore */ }
  }, []);

  const fetchUnread = useCallback(async () => {
    try {
      const r = await api.get("/chat/unread-count");
      setTotalUnread(r.data.unread_count || 0);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    Promise.all([fetchConversations(), fetchUnread()]).finally(() => setLoading(false));
  }, [fetchConversations, fetchUnread]);

  // Poll for new messages + conversations every 4s
  useEffect(() => {
    pollRef.current = setInterval(() => {
      fetchConversations();
      fetchUnread();
      if (activeConv) {
        api.get(`/chat/conversations/${activeConv.id}/messages`).then((r) => {
          setMessages(r.data.messages || []);
        }).catch(() => {});
      }
    }, 4000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [activeConv, fetchConversations, fetchUnread]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Open a conversation
  const openConversation = async (conv: ChatConversation) => {
    setActiveConv(conv);
    setMsgLoading(true);
    try {
      const r = await api.get(`/chat/conversations/${conv.id}/messages`);
      setMessages(r.data.messages || []);
      await fetchConversations();
      await fetchUnread();
    } catch (err) {
      console.error("Failed to load messages", err);
    } finally {
      setMsgLoading(false);
    }
  };

  // Send message
  const sendMessage = async () => {
    if (!newMsg.trim() || !activeConv || sending) return;
    setSending(true);
    try {
      await api.post(`/chat/conversations/${activeConv.id}/messages`, { message: newMsg.trim() });
      setNewMsg("");
      const r = await api.get(`/chat/conversations/${activeConv.id}/messages`);
      setMessages(r.data.messages || []);
      await fetchConversations();
    } catch (err) {
      console.error("Failed to send message", err);
    } finally {
      setSending(false);
    }
  };

  // Start new conversation
  const startNewConversation = async (user: ChatAvailableUser) => {
    try {
      const body: Record<string, unknown> = {
        other_user_id: user.id,
        subject: `Chat with ${user.name}`,
      };

      const r = await api.post("/chat/conversations", body);
      setShowNewChat(false);
      setUserSearch("");
      await fetchConversations();
      openConversation(r.data);
    } catch (err) {
      console.error("Failed to start conversation", getErrorMessage(err));
    }
  };

  // Fetch available users when new chat modal opens
  useEffect(() => {
    if (showNewChat) {
      api.get("/chat/available-users").then((r) => setAvailableUsers(r.data)).catch(() => {});
    }
  }, [showNewChat]);

  const filteredUsers = availableUsers.filter((u) =>
    u.name.toLowerCase().includes(userSearch.toLowerCase()) ||
    (u.business_name || "").toLowerCase().includes(userSearch.toLowerCase()) ||
    (u.organization || "").toLowerCase().includes(userSearch.toLowerCase())
  );

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60_000) return "Just now";
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
    if (diff < 86_400_000) return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  };

  const getDashboardLink = () => {
    if (!currentUser) return "/";
    if (currentUser.role === "vendor" && currentUser.vendor_id)
      return `/vendor/${currentUser.vendor_id}/dashboard`;
    if (currentUser.role === "lender" && currentUser.lender_id)
      return `/lender/${currentUser.lender_id}/dashboard`;
    return "/";
  };

  if (loading) return (
    <div className="min-h-screen bg-[#f8f9fc] flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mx-auto" />
        <p className="text-sm text-gray-500 mt-3">Loading messages...</p>
      </div>
    </div>
  );

  return (
    <ProtectedRoute>
    <div className="h-screen flex flex-col bg-[#f8f9fc]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-14">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-7 h-7 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-lg flex items-center justify-center">
                <FileText className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="text-lg font-bold text-gray-900">Invo<span className="text-indigo-600">X</span></span>
            </Link>
            <span className="text-gray-300">|</span>
            <div className="flex items-center gap-1.5">
              <MessageSquare className="w-4 h-4 text-indigo-600" />
              <span className="text-sm font-semibold text-gray-900">Messages</span>
              {totalUnread > 0 && (
                <span className="ml-1 px-1.5 py-0.5 bg-red-500 text-white rounded-full text-[10px] font-bold">{totalUnread}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/marketplace" className="text-xs text-gray-500 hover:text-gray-700 transition-colors">Marketplace</Link>
            <Link href={getDashboardLink()} className="text-xs text-gray-500 hover:text-gray-700 transition-colors">Dashboard</Link>
          </div>
        </div>
      </header>

      {/* Main Chat Area */}
      <div className="flex-1 flex overflow-hidden max-w-7xl mx-auto w-full">
        {/* Sidebar: Conversations */}
        <div className={`w-full sm:w-80 lg:w-96 bg-white border-r border-gray-100 flex flex-col ${activeConv ? "hidden sm:flex" : "flex"}`}>
          {/* Sidebar Header */}
          <div className="p-4 border-b border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-gray-900">Conversations</h2>
              <button
                onClick={() => setShowNewChat(true)}
                className="p-1.5 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
                title="New conversation"
              >
                <Plus className="w-4 h-4 text-indigo-600" />
              </button>
            </div>
          </div>

          {/* Conversation List */}
          <div className="flex-1 overflow-y-auto">
            {conversations.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-6">
                <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
                  <MessageSquare className="w-7 h-7 text-indigo-400" />
                </div>
                <p className="text-sm font-medium text-gray-700 mb-1">No conversations yet</p>
                <p className="text-xs text-gray-400 mb-4">Start a conversation with a {currentUser?.role === "vendor" ? "lender" : "vendor"}</p>
                <button
                  onClick={() => setShowNewChat(true)}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5 inline mr-1" /> New Message
                </button>
              </div>
            ) : (
              conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => openConversation(conv)}
                  className={`w-full p-4 text-left border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                    activeConv?.id === conv.id ? "bg-indigo-50 border-l-2 border-l-indigo-600" : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      conv.other_user_role === "lender"
                        ? "bg-gradient-to-br from-purple-500 to-indigo-600"
                        : "bg-gradient-to-br from-emerald-500 to-teal-600"
                    }`}>
                      <span className="text-white text-sm font-bold">{conv.other_user_name.charAt(0)}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900 truncate">{conv.other_user_name}</p>
                        <span className="text-[10px] text-gray-400 flex-shrink-0 ml-2">{formatTime(conv.last_message_at)}</span>
                      </div>
                      {conv.subject && (
                        <p className="text-[11px] text-indigo-500 truncate">{conv.subject}</p>
                      )}
                      <p className="text-xs text-gray-400 truncate mt-0.5">{conv.last_message || "No messages yet"}</p>
                    </div>
                    {conv.unread_count > 0 && (
                      <span className="w-5 h-5 bg-indigo-600 text-white rounded-full text-[10px] flex items-center justify-center font-bold flex-shrink-0">
                        {conv.unread_count}
                      </span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Message Area */}
        <div className={`flex-1 flex flex-col ${!activeConv ? "hidden sm:flex" : "flex"}`}>
          {!activeConv ? (
            /* Empty state */
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-20 h-20 bg-gradient-to-br from-indigo-100 to-purple-100 rounded-3xl flex items-center justify-center mx-auto mb-4">
                  <MessageSquare className="w-9 h-9 text-indigo-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-700 mb-1">Select a conversation</h3>
                <p className="text-sm text-gray-400">Choose from your existing conversations or start a new one</p>
              </div>
            </div>
          ) : (
            <>
              {/* Conversation Header */}
              <div className="bg-white border-b border-gray-100 px-4 py-3 flex items-center gap-3">
                <button
                  onClick={() => setActiveConv(null)}
                  className="sm:hidden p-1 hover:bg-gray-100 rounded-lg"
                >
                  <ArrowLeft className="w-5 h-5 text-gray-500" />
                </button>
                <div className={`w-9 h-9 rounded-full flex items-center justify-center ${
                  activeConv.other_user_role === "lender"
                    ? "bg-gradient-to-br from-purple-500 to-indigo-600"
                    : "bg-gradient-to-br from-emerald-500 to-teal-600"
                }`}>
                  <span className="text-white text-sm font-bold">{activeConv.other_user_name.charAt(0)}</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-gray-900">{activeConv.other_user_name}</p>
                  <p className="text-[11px] text-gray-400 capitalize">{activeConv.other_user_role}</p>
                </div>
                {activeConv.subject && (
                  <span className="text-[11px] bg-indigo-50 text-indigo-600 px-2 py-1 rounded-full hidden sm:block">
                    {activeConv.subject}
                  </span>
                )}
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
                {msgLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-center">
                    <div>
                      <MessageSquare className="w-10 h-10 text-gray-200 mx-auto mb-2" />
                      <p className="text-sm text-gray-400">No messages yet. Say hello!</p>
                    </div>
                  </div>
                ) : (
                  messages.map((msg) => {
                    const isMine = msg.sender_user_id === currentUser?.id;
                    return (
                      <div key={msg.id} className={`flex ${isMine ? "justify-end" : "justify-start"}`}>
                        {msg.message_type === "system" ? (
                          <div className="mx-auto bg-gray-100 text-gray-500 text-[11px] px-3 py-1 rounded-full">
                            {msg.message}
                          </div>
                        ) : (
                          <div className={`max-w-[75%] ${isMine ? "order-1" : ""}`}>
                            <div className={`px-4 py-2.5 rounded-2xl ${
                              isMine
                                ? "bg-indigo-600 text-white rounded-br-md"
                                : "bg-white text-gray-800 border border-gray-100 rounded-bl-md shadow-sm"
                            }`}>
                              <p className="text-sm whitespace-pre-wrap break-words">{msg.message}</p>
                            </div>
                            <div className={`flex items-center gap-1 mt-1 ${isMine ? "justify-end" : "justify-start"}`}>
                              <span className="text-[10px] text-gray-400">{formatTime(msg.created_at)}</span>
                              {isMine && (
                                <CheckCheck className={`w-3 h-3 ${msg.is_read ? "text-blue-400" : "text-gray-300"}`} />
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Message Input */}
              <div className="bg-white border-t border-gray-100 px-4 py-3">
                <div className="flex items-end gap-2">
                  <div className="flex-1 relative">
                    <textarea
                      value={newMsg}
                      onChange={(e) => setNewMsg(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          sendMessage();
                        }
                      }}
                      placeholder="Type a message..."
                      rows={1}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      style={{ maxHeight: "120px" }}
                    />
                  </div>
                  <button
                    onClick={sendMessage}
                    disabled={!newMsg.trim() || sending}
                    className="p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                  >
                    {sending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
                <p className="text-[10px] text-gray-300 mt-1">Press Enter to send, Shift+Enter for new line</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* New Conversation Modal */}
      {showNewChat && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[70vh] flex flex-col">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">New Conversation</h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Select a {currentUser?.role === "vendor" ? "lender" : "vendor"} to chat with
                </p>
              </div>
              <button onClick={() => { setShowNewChat(false); setUserSearch(""); }} className="p-1 hover:bg-gray-100 rounded-lg">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            {/* Search */}
            <div className="px-4 pt-3">
              <div className="relative">
                <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search by name, business, or organization..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            {/* User List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {filteredUsers.length === 0 ? (
                <div className="text-center py-8">
                  <Users className="w-8 h-8 text-gray-200 mx-auto mb-2" />
                  <p className="text-sm text-gray-400">No users found</p>
                </div>
              ) : (
                filteredUsers.map((user) => (
                  <button
                    key={user.id}
                    onClick={() => startNewConversation(user)}
                    className="w-full p-3 text-left rounded-xl border border-gray-100 hover:border-indigo-200 hover:bg-indigo-50/50 transition-colors flex items-center gap-3"
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      user.role === "lender"
                        ? "bg-gradient-to-br from-purple-500 to-indigo-600"
                        : "bg-gradient-to-br from-emerald-500 to-teal-600"
                    }`}>
                      <span className="text-white text-sm font-bold">{user.name.charAt(0)}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{user.name}</p>
                      <p className="text-xs text-gray-400 truncate">
                        {user.role === "lender"
                          ? (user.organization || "Individual Lender")
                          : (user.business_name || "Vendor")}
                      </p>
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      user.role === "lender"
                        ? "bg-purple-50 text-purple-600"
                        : "bg-emerald-50 text-emerald-600"
                    }`}>
                      {user.role}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
    </ProtectedRoute>
  );
}
