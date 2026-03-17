"use client";

import { useState, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { useAgentChat } from "@/lib/useAgentChat";
import FloatingBubble from "./FloatingBubble";
import AssistantPanel from "./AssistantPanel";

export default function FloatingAssistant() {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  const handleNavigate = useCallback(
    (path: string) => {
      router.push(path);
    },
    [router]
  );

  const {
    messages, loading, conversationId, suggestions,
    sendMessage, stopGeneration, clearChat, loadConversation,
  } = useAgentChat({ onNavigate: handleNavigate });

  useEffect(() => {
    setMounted(true);
  }, []);

  // Keyboard shortcut: Ctrl+/
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "/") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (!mounted) return null;

  return createPortal(
    <>
      <FloatingBubble open={open} onClick={() => setOpen(!open)} />
      <AssistantPanel
        open={open}
        onClose={() => setOpen(false)}
        messages={messages}
        loading={loading}
        conversationId={conversationId}
        suggestions={suggestions}
        onSend={sendMessage}
        onStop={stopGeneration}
        onClear={clearChat}
        onLoadConversation={loadConversation}
      />
    </>,
    document.body
  );
}
