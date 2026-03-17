"use client";

import { useEffect, useState } from "react";
import { Card, Typography, Descriptions, Avatar, Tag, Spin } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { getUser } from "@/lib/auth";
import type { User } from "@/types";
import { formatDate } from "@/lib/utils";

const { Title, Text } = Typography;

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  if (!user) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>;
  }

  return (
    <div className="page-fade-in" style={{ maxWidth: 640 }}>
      <div className="page-header">
        <Title level={2}>个人信息</Title>
      </div>

      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 24 }}>
          <Avatar
            size={72}
            style={{ background: "linear-gradient(135deg, #4f6ef7, #7c5cf7)", flexShrink: 0 }}
            icon={<UserOutlined />}
          />
          <div>
            <Title level={4} style={{ margin: 0 }}>{user.full_name || user.username}</Title>
            <Text type="secondary">{user.email}</Text>
          </div>
        </div>

        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
          <Descriptions.Item label="全名">{user.full_name || "-"}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={user.is_active ? "success" : "default"}>{user.is_active ? "已激活" : "未激活"}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="角色">
            <Tag color={user.is_admin ? "blue" : "default"}>{user.is_admin ? "管理员" : "普通用户"}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="注册时间">{formatDate(user.created_at)}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
