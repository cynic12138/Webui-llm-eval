"use client";

import { useEffect, useState } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Card, Typography,
  Tag, Space, Popconfirm, message, Switch, Alert, Collapse, Slider, InputNumber,
} from "antd";
import {
  PlusOutlined, DeleteOutlined, EditOutlined,
  StarOutlined, StarFilled, SafetyCertificateOutlined, ApiOutlined,
} from "@ant-design/icons";
import { judgeModelsApi } from "@/lib/api";
import type { JudgeModelConfig } from "@/types";

const { Title, Text, Paragraph } = Typography;

const PROVIDERS = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "dashscope", label: "DashScope (通义千问)" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "zhipu", label: "智谱 (GLM)" },
  { value: "baidu", label: "百度 (文心一言)" },
  { value: "custom", label: "自定义 OpenAI 兼容" },
];

const RECOMMENDED_MODELS = [
  { provider: "openai", model: "gpt-4o", desc: "OpenAI 旗舰模型，推理能力强" },
  { provider: "anthropic", model: "claude-sonnet-4-20250514", desc: "Anthropic 最新模型" },
  { provider: "dashscope", model: "qwen-max", desc: "通义千问旗舰模型" },
  { provider: "deepseek", model: "deepseek-chat", desc: "DeepSeek V3" },
];

export default function JudgeModelsPage() {
  const [judgeModels, setJudgeModels] = useState<JudgeModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);

  const handleTestConnection = async (id: number) => {
    setTestingId(id);
    try {
      const res = await judgeModelsApi.test(id);
      if (res.success) {
        message.success(`连接成功 (${res.latency_ms}ms): ${res.output?.slice(0, 60) || "OK"}`);
      } else {
        message.error(`连接失败: ${res.error || "未知错误"}`);
      }
    } catch {
      message.error("测试请求失败");
    } finally {
      setTestingId(null);
    }
  };

  const loadModels = async () => {
    setLoading(true);
    try {
      setJudgeModels(await judgeModelsApi.list());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadModels(); }, []);

  const handleSubmit = async (values: {
    name: string; provider: string; api_key?: string;
    base_url?: string; model_name: string; is_default?: boolean;
    params?: Record<string, unknown>;
  }) => {
    setSubmitting(true);
    try {
      if (editingId) {
        await judgeModelsApi.update(editingId, values);
        message.success("更新成功");
      } else {
        await judgeModelsApi.create(values);
        message.success("裁判模型添加成功");
      }
      setModalOpen(false);
      setEditingId(null);
      form.resetFields();
      loadModels();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      message.error(axiosError?.response?.data?.detail || "操作失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (record: JudgeModelConfig) => {
    setEditingId(record.id);
    form.setFieldsValue({
      name: record.name,
      provider: record.provider,
      base_url: record.base_url,
      model_name: record.model_name,
      is_default: record.is_default,
      params: record.params || {},
    });
    setModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await judgeModelsApi.delete(id);
      message.success("已删除");
      loadModels();
    } catch {
      message.error("删除失败");
    }
  };

  const handleSetDefault = async (id: number) => {
    try {
      await judgeModelsApi.update(id, { is_default: true });
      message.success("已设为默认");
      loadModels();
    } catch {
      message.error("操作失败");
    }
  };

  const columns = [
    {
      title: "名称", dataIndex: "name", key: "name",
      render: (name: string, record: JudgeModelConfig) => (
        <Space>
          {record.is_default && <StarFilled style={{ color: "#faad14" }} />}
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: "供应商", dataIndex: "provider", key: "provider",
      render: (p: string) => <Tag color="blue">{p}</Tag>,
    },
    { title: "模型", dataIndex: "model_name", key: "model_name" },
    { title: "API地址", dataIndex: "base_url", key: "base_url", ellipsis: true },
    {
      title: "状态", dataIndex: "is_active", key: "is_active",
      render: (active: boolean) => active
        ? <Tag color="success">启用</Tag>
        : <Tag color="default">停用</Tag>,
    },
    {
      title: "操作", key: "action", width: 280,
      render: (_: unknown, record: JudgeModelConfig) => (
        <Space wrap size={[4, 4]}>
          <Button
            size="small"
            icon={<ApiOutlined />}
            loading={testingId === record.id}
            onClick={() => handleTestConnection(record.id)}
          >
            测试
          </Button>
          {!record.is_default && (
            <Button size="small" icon={<StarOutlined />} onClick={() => handleSetDefault(record.id)}>
              默认
            </Button>
          )}
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <div>
          <Title level={2}><SafetyCertificateOutlined /> 裁判模型配置</Title>
          <Text type="secondary">
            配置用于 LLM-as-Judge 评分和领域评测的高级裁判模型，与通用模型管理独立
          </Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingId(null); form.resetFields(); setModalOpen(true); }}>
          添加裁判模型
        </Button>
      </div>

      {judgeModels.length === 0 && !loading && (
        <Alert
          type="info"
          showIcon
          message="尚未配置裁判模型"
          description={
            <div>
              <Paragraph>裁判模型是用于 LLM-as-Judge 评分的独立高能力模型。建议使用以下模型作为裁判：</Paragraph>
              <Space wrap>
                {RECOMMENDED_MODELS.map((rm) => (
                  <Tag
                    key={rm.model}
                    color="blue"
                    style={{ cursor: "pointer" }}
                    onClick={() => {
                      form.setFieldsValue({
                        name: `${rm.model} (Judge)`,
                        provider: rm.provider,
                        model_name: rm.model,
                        is_default: judgeModels.length === 0,
                      });
                      setEditingId(null);
                      setModalOpen(true);
                    }}
                  >
                    {rm.model} - {rm.desc}
                  </Tag>
                ))}
              </Space>
            </div>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      <Card>
        <Table
          dataSource={judgeModels}
          columns={columns}
          rowKey="id"
          loading={loading}
          scroll={{ x: 800 }}
          locale={{ emptyText: "暂无裁判模型，点击上方按钮添加" }}
        />
      </Card>

      <Modal
        title={editingId ? "编辑裁判模型" : "添加裁判模型"}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null); form.resetFields(); }}
        footer={null}
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 16 }}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如：GPT-4o Judge" />
          </Form.Item>
          <Form.Item name="provider" label="供应商" rules={[{ required: true }]}>
            <Select options={PROVIDERS} placeholder="选择模型供应商" />
          </Form.Item>
          <Form.Item name="model_name" label="模型标识" rules={[{ required: true }]}>
            <Input placeholder="如：gpt-4o, claude-sonnet-4-20250514, qwen-max" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key">
            <Input.Password placeholder={editingId ? "留空保持不变" : "输入 API Key"} />
          </Form.Item>
          <Form.Item name="base_url" label="API 地址">
            <Input placeholder="如：https://api.openai.com/v1（留空使用默认）" />
          </Form.Item>
          <Form.Item name="is_default" valuePropName="checked" label="设为默认裁判模型">
            <Switch />
          </Form.Item>
          <Collapse
            ghost
            items={[{
              key: "params",
              label: <Text type="secondary">高级参数 (temperature, top_p, top_k, 重复惩罚等)</Text>,
              children: (
                <div>
                  <Form.Item name={["params", "temperature"]} label="Temperature">
                    <Slider min={0} max={2} step={0.1} marks={{ 0: "精确", 0.7: "平衡", 1.5: "创意", 2: "随机" }} />
                  </Form.Item>
                  <Form.Item name={["params", "max_tokens"]} label="最大输出 Token 数">
                    <InputNumber min={1} max={65536} step={256} style={{ width: "100%" }} placeholder="默认 2048" />
                  </Form.Item>
                  <Form.Item name={["params", "top_p"]} label="Top P (核采样)">
                    <Slider min={0} max={1} step={0.05} marks={{ 0: "0", 0.9: "0.9", 1: "1" }} />
                  </Form.Item>
                  <Form.Item name={["params", "top_k"]} label="Top K">
                    <InputNumber min={1} max={100} style={{ width: "100%" }} placeholder="不设置则使用模型默认值" />
                  </Form.Item>
                  <Form.Item name={["params", "repetition_penalty"]} label="重复惩罚">
                    <Slider min={1.0} max={2.0} step={0.05} marks={{ 1: "1.0", 1.1: "1.1", 1.5: "1.5", 2: "2.0" }} />
                  </Form.Item>
                  <Form.Item name={["params", "presence_penalty"]} label="存在惩罚 (Presence Penalty)">
                    <Slider min={-2.0} max={2.0} step={0.1} marks={{ "-2": "-2", 0: "0", 1.5: "1.5", 2: "2" }} />
                  </Form.Item>
                </div>
              ),
            }]}
            style={{ marginBottom: 8 }}
          />
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={submitting}>
                {editingId ? "更新" : "添加"}
              </Button>
              <Button onClick={() => setModalOpen(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
