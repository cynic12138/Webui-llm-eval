"use client";

import { useEffect, useState } from "react";
import { Table, Typography, Tag, Select, Input, DatePicker, Space, Card } from "antd";
import { AuditOutlined } from "@ant-design/icons";
import { auditApi } from "@/lib/api";
import type { AuditLog } from "@/types";
import dayjs from "dayjs";

const { Title } = Typography;
const { RangePicker } = DatePicker;

const ACTION_COLORS: Record<string, string> = {
  "user.login": "blue",
  "evaluation.create": "purple",
  "evaluation.retry": "orange",
  "model.create": "green",
  "model.delete": "red",
  "dataset.delete": "red",
};

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState<string>();

  const loadLogs = (params?: { action?: string }) => {
    setLoading(true);
    auditApi.logs({ ...params, limit: 100 })
      .then(setLogs)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const columns = [
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm:ss"),
    },
    {
      title: "用户ID",
      dataIndex: "user_id",
      key: "user_id",
      width: 80,
    },
    {
      title: "操作",
      dataIndex: "action",
      key: "action",
      width: 160,
      render: (v: string) => (
        <Tag color={ACTION_COLORS[v] || "default"}>{v}</Tag>
      ),
    },
    {
      title: "资源类型",
      dataIndex: "resource_type",
      key: "resource_type",
      width: 140,
      render: (v: string) => v || "-",
    },
    {
      title: "资源ID",
      dataIndex: "resource_id",
      key: "resource_id",
      width: 80,
      render: (v: number) => v ?? "-",
    },
    {
      title: "IP地址",
      dataIndex: "ip_address",
      key: "ip_address",
      width: 130,
      render: (v: string) => v || "-",
    },
    {
      title: "详情",
      dataIndex: "details",
      key: "details",
      ellipsis: true,
      render: (v: Record<string, unknown>) => v ? JSON.stringify(v) : "-",
    },
  ];

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <div>
          <Title level={2}>
            <AuditOutlined style={{ marginRight: 8 }} />
            审计日志
          </Title>
          <span className="page-subtitle">系统操作审计记录</span>
        </div>
      </div>

      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="按操作过滤"
            allowClear
            style={{ width: 200 }}
            value={actionFilter}
            onChange={(v) => {
              setActionFilter(v);
              loadLogs({ action: v });
            }}
            options={[
              { value: "user.login", label: "用户登录" },
              { value: "evaluation.create", label: "创建评测" },
              { value: "evaluation.retry", label: "重试评测" },
              { value: "model.create", label: "创建模型" },
              { value: "model.delete", label: "删除模型" },
            ]}
          />
        </Space>

        <Table
          dataSource={logs}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
}
