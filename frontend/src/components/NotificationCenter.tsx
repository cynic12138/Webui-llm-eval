"use client";

import { useState, useEffect, useCallback } from "react";
import { Drawer, List, Badge, Button, Typography, Tag, Empty, Space, message } from "antd";
import { BellOutlined, CheckOutlined, DeleteOutlined } from "@ant-design/icons";
import { notificationsApi } from "@/lib/api";
import { useRouter } from "next/navigation";
import { formatDate } from "@/lib/utils";

const { Text, Paragraph } = Typography;

interface NotifItem {
  id: number;
  type: string;
  title: string;
  message?: string;
  data?: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

const typeColors: Record<string, string> = {
  evaluation_completed: "success",
  evaluation_failed: "error",
  system: "processing",
};

export default function NotificationCenter() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotifItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const loadUnreadCount = useCallback(() => {
    notificationsApi.unreadCount().then((r) => setUnreadCount(r.count)).catch(() => {});
  }, []);

  useEffect(() => {
    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [loadUnreadCount]);

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const items = await notificationsApi.list({ limit: 50 });
      setNotifications(items);
    } finally {
      setLoading(false);
    }
  };

  const handleOpen = () => { setOpen(true); loadNotifications(); };

  const handleMarkRead = async (id: number) => {
    await notificationsApi.markRead(id);
    setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n));
    setUnreadCount((c) => Math.max(0, c - 1));
  };

  const handleMarkAllRead = async () => {
    await notificationsApi.markAllRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
    message.success("全部已读");
  };

  const handleDelete = async (id: number) => {
    await notificationsApi.delete(id);
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    loadUnreadCount();
  };

  const handleClick = (item: NotifItem) => {
    if (!item.is_read) handleMarkRead(item.id);
    const taskId = item.data?.task_id;
    if (taskId) { router.push(`/evaluations/${taskId}`); setOpen(false); }
  };

  return (
    <>
      <Button type="text" className="header-toggle-btn" onClick={handleOpen}>
        <Badge count={unreadCount} size="small" offset={[-2, 2]}>
          <BellOutlined style={{ fontSize: 18 }} />
        </Badge>
      </Button>

      <Drawer
        title="通知中心"
        open={open}
        onClose={() => setOpen(false)}
        width={400}
        extra={unreadCount > 0 && <Button size="small" icon={<CheckOutlined />} onClick={handleMarkAllRead}>全部已读</Button>}
      >
        {notifications.length === 0 ? (
          <Empty description="暂无通知" />
        ) : (
          <List
            loading={loading}
            dataSource={notifications}
            renderItem={(item) => (
              <List.Item
                style={{
                  cursor: "pointer",
                  background: item.is_read ? "transparent" : "var(--bg-hover, #f6f8fa)",
                  padding: "12px", borderRadius: 8, marginBottom: 4,
                }}
                onClick={() => handleClick(item)}
                actions={[
                  <Button key="del" type="text" size="small" icon={<DeleteOutlined />}
                    onClick={(e) => { e.stopPropagation(); handleDelete(item.id); }} />,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      {!item.is_read && <Badge status="processing" />}
                      <Tag color={typeColors[item.type] || "default"}>{item.type}</Tag>
                      <Text strong={!item.is_read}>{item.title}</Text>
                    </Space>
                  }
                  description={
                    <>
                      {item.message && <Paragraph type="secondary" style={{ marginBottom: 4, fontSize: 12 }}>{item.message}</Paragraph>}
                      <Text type="secondary" style={{ fontSize: 11 }}>{formatDate(item.created_at)}</Text>
                    </>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Drawer>
    </>
  );
}
