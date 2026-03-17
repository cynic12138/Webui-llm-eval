"use client";

import { useState } from "react";
import { Button, Tabs } from "antd";
import {
  CloseOutlined, MessageOutlined,
  ToolOutlined, HistoryOutlined, ClearOutlined, BulbOutlined,
} from "@ant-design/icons";
import type { ChatMessage } from "@/types";
import ChatView from "./ChatView";
import ToolsPanel from "./ToolsPanel";
import HistoryPanel from "./HistoryPanel";
import MemoryPanel from "./MemoryPanel";

interface AssistantPanelProps {
  open: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  loading: boolean;
  conversationId: number | null;
  suggestions?: {label: string; prompt: string}[];
  onSend: (msg: string) => void;
  onStop: () => void;
  onClear: () => void;
  onLoadConversation: (id: number) => void;
}

export default function AssistantPanel({
  open, onClose, messages, loading, conversationId, suggestions,
  onSend, onStop, onClear, onLoadConversation,
}: AssistantPanelProps) {
  const [activeTab, setActiveTab] = useState("chat");

  return (
    <div className={`agent-panel ${open ? "agent-panel--open" : ""}`}>
      <div className="agent-panel-header">
        <div className="agent-panel-header-left">
          <div className="agent-panel-title-icon">
            <MessageOutlined />
          </div>
          <span className="agent-panel-title">AI 助手</span>
        </div>
        <div className="agent-panel-header-right">
          <Button
            type="text"
            size="small"
            icon={<ClearOutlined />}
            onClick={onClear}
            title="新对话"
          />
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            onClick={onClose}
          />
        </div>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        size="small"
        className="agent-panel-tabs"
        items={[
          {
            key: "chat",
            label: (
              <span><MessageOutlined /> 对话</span>
            ),
            children: (
              <ChatView
                messages={messages}
                loading={loading}
                onSend={onSend}
                onStop={onStop}
                suggestions={suggestions}
              />
            ),
          },
          {
            key: "tools",
            label: (
              <span><ToolOutlined /> 工具</span>
            ),
            children: <ToolsPanel />,
          },
          {
            key: "history",
            label: (
              <span><HistoryOutlined /> 历史</span>
            ),
            children: (
              <HistoryPanel
                activeConversationId={conversationId}
                onSelect={(id) => {
                  onLoadConversation(id);
                  setActiveTab("chat");
                }}
                onNewChat={() => {
                  onClear();
                  setActiveTab("chat");
                }}
              />
            ),
          },
          {
            key: "memory",
            label: (
              <span><BulbOutlined /> 记忆</span>
            ),
            children: <MemoryPanel />,
          },
        ]}
      />
    </div>
  );
}
