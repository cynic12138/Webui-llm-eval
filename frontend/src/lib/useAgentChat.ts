"use client";

import { useState, useCallback, useRef } from "react";
import { usePathname } from "next/navigation";
import { agentApi } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ChatMessage } from "@/types";

interface UseAgentChatOptions {
  onNavigate?: (path: string) => void;
}

export function useAgentChat(options: UseAgentChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [suggestions, setSuggestions] = useState<{label: string; prompt: string}[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const pathname = usePathname();

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || loading) return;

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date(),
      };

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "",
        toolCalls: [],
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setSuggestions([]);
      setLoading(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const token = getToken();
        const resp = await fetch(agentApi.chatStreamUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            message: text,
            conversation_id: conversationId,
            context: { current_route: pathname },
          }),
          signal: controller.signal,
        });

        if (!resp.ok) {
          throw new Error(`HTTP ${resp.status}`);
        }

        const reader = resp.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let eventType = "";
          let eventData = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              eventData = line.slice(6);
              if (eventType && eventData) {
                processEvent(eventType, eventData, assistantMsg.id);
                eventType = "";
                eventData = "";
              }
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, content: m.content + "\n\n[连接错误，请重试]" }
              : m
          )
        );
      } finally {
        setLoading(false);
        abortRef.current = null;
      }
    },
    [conversationId, loading] // eslint-disable-line react-hooks/exhaustive-deps
  );

  const processEvent = useCallback(
    (type: string, rawData: string, assistantId: string) => {
      try {
        const data = JSON.parse(rawData);
        switch (type) {
          case "message_start":
            setConversationId(data.conversation_id);
            break;

          case "content_delta":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + data.content }
                  : m
              )
            );
            break;

          case "tool_call_start":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      toolCalls: [
                        ...(m.toolCalls || []),
                        {
                          id: data.tool_call_id,
                          name: data.name,
                          arguments: data.arguments,
                          status: "running" as const,
                        },
                      ],
                    }
                  : m
              )
            );
            break;

          case "tool_result":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      toolCalls: (m.toolCalls || []).map((tc) =>
                        tc.id === data.tool_call_id
                          ? {
                              ...tc,
                              status: data.result?.error ? ("error" as const) : ("done" as const),
                              result: data.result,
                            }
                          : tc
                      ),
                    }
                  : m
              )
            );
            break;

          case "suggestions":
            setSuggestions(data.suggestions || []);
            break;

          case "navigate":
            options.onNavigate?.(data.path);
            break;

          case "error":
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + `\n\n**错误**: ${data.error}` }
                  : m
              )
            );
            break;
        }
      } catch {
        // ignore malformed events
      }
    },
    [options] // eslint-disable-line react-hooks/exhaustive-deps
  );

  const stopGeneration = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
  }, []);

  const loadConversation = useCallback(async (convId: number) => {
    try {
      const detail = await agentApi.conversation(convId);
      setConversationId(convId);

      const chatMessages: ChatMessage[] = [];
      for (const msg of detail.messages) {
        if (msg.role === "user") {
          chatMessages.push({
            id: `msg-${msg.id}`,
            role: "user",
            content: msg.content || "",
            timestamp: new Date(msg.created_at),
          });
        } else if (msg.role === "assistant") {
          chatMessages.push({
            id: `msg-${msg.id}`,
            role: "assistant",
            content: msg.content || "",
            toolCalls: msg.tool_calls?.map((tc) => ({
              id: tc.id,
              name: tc.function.name,
              arguments: JSON.parse(tc.function.arguments || "{}"),
              status: "done" as const,
            })),
            timestamp: new Date(msg.created_at),
          });
        }
        // tool messages are shown as part of the assistant message's toolCalls
      }
      setMessages(chatMessages);
    } catch {
      // ignore
    }
  }, []);

  return {
    messages,
    loading,
    conversationId,
    suggestions,
    sendMessage,
    stopGeneration,
    clearChat,
    loadConversation,
  };
}
