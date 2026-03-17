"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Checkbox, Tag, Badge, message,
  Typography, Collapse, Space, Popconfirm, Tooltip, Card,
} from "antd";
import {
  PlusOutlined, DeleteOutlined, CopyOutlined, KeyOutlined,
  CheckCircleOutlined, StopOutlined, SwapOutlined, EyeOutlined,
} from "@ant-design/icons";
import { apiKeysApi } from "@/lib/api";
import type { APIKeyItem } from "@/types";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

const PERMISSION_OPTIONS = [
  { label: "读取 (read)", value: "read" },
  { label: "写入 (write)", value: "write" },
  { label: "评测 (evaluate)", value: "evaluate" },
];

const permissionColorMap: Record<string, string> = {
  read: "blue",
  write: "orange",
  evaluate: "green",
};

export default function APIKeysPage() {
  const [keys, setKeys] = useState<APIKeyItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [createdKeyModalOpen, setCreatedKeyModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();

  const fetchKeys = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiKeysApi.list();
      setKeys(data);
    } catch {
      message.error("加载 API 密钥列表失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleCreate = async (values: { name: string; permissions: string[]; expires_in_days?: number }) => {
    setCreating(true);
    try {
      const data = await apiKeysApi.create({
        name: values.name,
        permissions: values.permissions,
        expires_in_days: values.expires_in_days || undefined,
      });
      setCreatedKey(data.key);
      setCreateModalOpen(false);
      setCreatedKeyModalOpen(true);
      form.resetFields();
      message.success(data.message || "API Key 创建成功");
      fetchKeys();
    } catch {
      message.error("创建 API Key 失败");
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: number) => {
    try {
      const data = await apiKeysApi.revoke(id);
      message.success(data.message || "已撤销");
      fetchKeys();
    } catch {
      message.error("撤销失败");
    }
  };

  const handleToggle = async (id: number) => {
    try {
      const data = await apiKeysApi.toggle(id);
      message.success(data.message || "操作成功");
      fetchKeys();
    } catch {
      message.error("操作失败");
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      message.success("已复制到剪贴板");
    }).catch(() => {
      message.error("复制失败，请手动复制");
    });
  };

  const columns: ColumnsType<APIKeyItem> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: "密钥前缀",
      dataIndex: "key_prefix",
      key: "key_prefix",
      render: (prefix: string) => (
        <Text code>{prefix}••••••••</Text>
      ),
    },
    {
      title: "权限",
      dataIndex: "permissions",
      key: "permissions",
      render: (permissions: string[]) => (
        <Space size={4} wrap>
          {permissions.map((p) => (
            <Tag key={p} color={permissionColorMap[p] || "default"}>
              {p}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (active: boolean) =>
        active ? (
          <Badge status="success" text="启用" />
        ) : (
          <Badge status="error" text="已撤销" />
        ),
    },
    {
      title: "最后使用",
      dataIndex: "last_used_at",
      key: "last_used_at",
      render: (val: string | null) =>
        val ? dayjs(val).format("YYYY-MM-DD HH:mm") : <Text type="secondary">从未使用</Text>,
    },
    {
      title: "过期时间",
      dataIndex: "expires_at",
      key: "expires_at",
      render: (val: string | null) => {
        if (!val) return <Text type="secondary">永不过期</Text>;
        const expired = dayjs(val).isBefore(dayjs());
        return (
          <Text type={expired ? "danger" : undefined}>
            {dayjs(val).format("YYYY-MM-DD HH:mm")}
            {expired && " (已过期)"}
          </Text>
        );
      },
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (val: string) => dayjs(val).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "操作",
      key: "actions",
      render: (_: unknown, record: APIKeyItem) => (
        <Space>
          <Tooltip title={record.is_active ? "禁用" : "启用"}>
            <Button
              type="text"
              size="small"
              icon={record.is_active ? <StopOutlined /> : <CheckCircleOutlined />}
              onClick={() => handleToggle(record.id)}
            />
          </Tooltip>
          {record.is_active && (
            <Popconfirm
              title="确定要撤销此 API Key 吗？"
              description="撤销后将无法再使用此密钥进行 API 调用。"
              onConfirm={() => handleRevoke(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="撤销">
                <Button type="text" size="small" danger icon={<DeleteOutlined />} />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <KeyOutlined style={{ marginRight: 8 }} />
          API 密钥管理
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
          创建密钥
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={keys}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: "暂无 API 密钥，点击「创建密钥」开始使用" }}
      />

      {/* Create API Key Modal */}
      <Modal
        title="创建 API 密钥"
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ permissions: ["read"] }}
        >
          <Form.Item
            name="name"
            label="密钥名称"
            rules={[{ required: true, message: "请输入密钥名称" }]}
          >
            <Input placeholder="例如：CI/CD Pipeline、数据分析脚本" maxLength={100} />
          </Form.Item>
          <Form.Item
            name="permissions"
            label="权限"
            rules={[{ required: true, message: "请至少选择一个权限" }]}
          >
            <Checkbox.Group options={PERMISSION_OPTIONS} />
          </Form.Item>
          <Form.Item
            name="expires_in_days"
            label="过期天数（可选）"
            extra="留空表示永不过期"
          >
            <Input type="number" placeholder="例如：30、90、365" min={1} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Show Created Key Modal */}
      <Modal
        title="API 密钥已创建"
        open={createdKeyModalOpen}
        onCancel={() => {
          setCreatedKeyModalOpen(false);
          setCreatedKey(null);
        }}
        footer={[
          <Button
            key="copy"
            type="primary"
            icon={<CopyOutlined />}
            onClick={() => createdKey && handleCopy(createdKey)}
          >
            复制密钥
          </Button>,
          <Button
            key="close"
            onClick={() => {
              setCreatedKeyModalOpen(false);
              setCreatedKey(null);
            }}
          >
            关闭
          </Button>,
        ]}
      >
        <div style={{ marginBottom: 16 }}>
          <Text type="warning" strong>
            请立即复制并妥善保管此密钥，关闭后将无法再次查看！
          </Text>
        </div>
        <Input.TextArea
          value={createdKey || ""}
          readOnly
          autoSize={{ minRows: 2 }}
          style={{ fontFamily: "monospace", fontSize: 14 }}
        />
      </Modal>

      {/* API Documentation */}
      <Card style={{ marginTop: 24 }}>
        <Collapse ghost>
          <Panel header={<Text strong>API 使用文档</Text>} key="docs">
            <div>
              <Title level={5}>认证方式</Title>
              <Paragraph>
                在 HTTP 请求头中添加 <Text code>X-API-Key</Text> 字段，值为您的 API 密钥。
              </Paragraph>

              <Title level={5}>使用示例</Title>

              <Paragraph>
                <Text strong>cURL:</Text>
              </Paragraph>
              <Paragraph>
                <pre style={{
                  background: "var(--ant-color-bg-layout)",
                  padding: 12,
                  borderRadius: 6,
                  overflow: "auto",
                }}>
{`curl -H "X-API-Key: your-key-here" \\
  https://your-domain/api/v1/evaluations/`}
                </pre>
              </Paragraph>

              <Paragraph>
                <Text strong>Python:</Text>
              </Paragraph>
              <Paragraph>
                <pre style={{
                  background: "var(--ant-color-bg-layout)",
                  padding: 12,
                  borderRadius: 6,
                  overflow: "auto",
                }}>
{`import requests

headers = {"X-API-Key": "your-key-here"}
response = requests.get(
    "https://your-domain/api/v1/evaluations/",
    headers=headers
)
print(response.json())`}
                </pre>
              </Paragraph>

              <Paragraph>
                <Text strong>JavaScript (fetch):</Text>
              </Paragraph>
              <Paragraph>
                <pre style={{
                  background: "var(--ant-color-bg-layout)",
                  padding: 12,
                  borderRadius: 6,
                  overflow: "auto",
                }}>
{`const response = await fetch("https://your-domain/api/v1/evaluations/", {
  headers: { "X-API-Key": "your-key-here" }
});
const data = await response.json();`}
                </pre>
              </Paragraph>

              <Title level={5}>权限说明</Title>
              <Paragraph>
                <ul>
                  <li><Tag color="blue">read</Tag> - 读取评测任务、数据集、模型配置等信息</li>
                  <li><Tag color="orange">write</Tag> - 创建和修改资源</li>
                  <li><Tag color="green">evaluate</Tag> - 创建和运行评测任务</li>
                </ul>
              </Paragraph>

              <Title level={5}>注意事项</Title>
              <Paragraph>
                <ul>
                  <li>API 密钥仅在创建时显示一次，请妥善保管</li>
                  <li>如果密钥泄露，请立即撤销并创建新密钥</li>
                  <li>过期的密钥将自动失效，无法用于 API 调用</li>
                  <li>撤销后的密钥无法恢复，需要重新创建</li>
                </ul>
              </Paragraph>
            </div>
          </Panel>
        </Collapse>
      </Card>
    </div>
  );
}
