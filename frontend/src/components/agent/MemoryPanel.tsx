"use client";

import { useState, useEffect } from "react";
import { List, Tag, Button, Empty, Popconfirm, message, Typography, Space } from "antd";
import { DeleteOutlined, ClearOutlined, BulbOutlined } from "@ant-design/icons";
import { agentApi } from "@/lib/api";
import type { AgentMemoryItem } from "@/types";

const { Text } = Typography;

const typeColors: Record<string, string> = {
  preference: "blue",
  context: "green",
  insight: "purple",
};

const typeLabels: Record<string, string> = {
  preference: "偏好",
  context: "上下文",
  insight: "洞察",
};

export default function MemoryPanel() {
  const [memories, setMemories] = useState<AgentMemoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const items = await agentApi.memories();
      setMemories(items);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id: number) => {
    await agentApi.deleteMemory(id);
    setMemories((prev) => prev.filter((m) => m.id !== id));
    message.success("已删除");
  };

  const handleClearAll = async () => {
    await agentApi.clearMemories();
    setMemories([]);
    message.success("已清除所有记忆");
  };

  return (
    <div style={{ padding: "8px 0" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, padding: "0 4px" }}>
        <Space>
          <BulbOutlined />
          <Text strong>AI 助手记忆</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>({memories.length})</Text>
        </Space>
        {memories.length > 0 && (
          <Popconfirm title="确定清除所有记忆？" onConfirm={handleClearAll}>
            <Button type="text" size="small" danger icon={<ClearOutlined />}>清除</Button>
          </Popconfirm>
        )}
      </div>

      {memories.length === 0 ? (
        <Empty
          description="AI 助手尚未保存任何记忆"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ margin: "40px 0" }}
        />
      ) : (
        <List
          loading={loading}
          dataSource={memories}
          size="small"
          renderItem={(item) => (
            <List.Item
              style={{ padding: "8px 4px", borderBottom: "1px solid var(--border-color, #f0f0f0)" }}
              actions={[
                <Button
                  key="del"
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleDelete(item.id)}
                />,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space size={4}>
                    <Tag color={typeColors[item.memory_type] || "default"} style={{ margin: 0 }}>
                      {typeLabels[item.memory_type] || item.memory_type}
                    </Tag>
                    <Text strong style={{ fontSize: 13 }}>{item.key}</Text>
                  </Space>
                }
                description={
                  <Text type="secondary" style={{ fontSize: 12 }}>{item.value}</Text>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );
}
