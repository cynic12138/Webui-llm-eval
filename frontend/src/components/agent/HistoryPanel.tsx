"use client";

import { useEffect, useState } from "react";
import { Spin, Empty, Button } from "antd";
import { DeleteOutlined, MessageOutlined, PlusOutlined } from "@ant-design/icons";
import { agentApi } from "@/lib/api";
import type { AgentConversation } from "@/types";
import dayjs from "dayjs";

interface HistoryPanelProps {
  activeConversationId: number | null;
  onSelect: (id: number) => void;
  onNewChat: () => void;
}

export default function HistoryPanel({ activeConversationId, onSelect, onNewChat }: HistoryPanelProps) {
  const [conversations, setConversations] = useState<AgentConversation[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    agentApi.conversations().then(setConversations).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    await agentApi.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
  };

  if (loading) {
    return <div className="agent-panel-loading"><Spin size="small" /></div>;
  }

  return (
    <div className="agent-history-panel">
      <div className="agent-history-header">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          size="small"
          onClick={onNewChat}
          block
        >
          新对话
        </Button>
      </div>

      {conversations.length === 0 ? (
        <Empty description="暂无历史对话" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div className="agent-history-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`agent-history-item ${conv.id === activeConversationId ? "agent-history-item--active" : ""}`}
              onClick={() => onSelect(conv.id)}
            >
              <MessageOutlined className="agent-history-item-icon" />
              <div className="agent-history-item-content">
                <div className="agent-history-item-title">{conv.title}</div>
                <div className="agent-history-item-time">
                  {dayjs(conv.updated_at).format("MM-DD HH:mm")}
                </div>
              </div>
              <Button
                type="text"
                size="small"
                icon={<DeleteOutlined />}
                className="agent-history-item-delete"
                onClick={(e) => handleDelete(e, conv.id)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
