"use client";

import { useEffect, useState } from "react";
import {
  Card, Button, Form, Input, Select, Typography,
  Space, message, InputNumber, Slider, Alert, Spin, Popconfirm, Tag, Collapse,
} from "antd";
import { RobotOutlined, DeleteOutlined, SaveOutlined, ApiOutlined } from "@ant-design/icons";
import { agentModelApi } from "@/lib/api";
import type { AgentModelConfig } from "@/types";

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
  { provider: "openai", model: "gpt-4o", base_url: "https://api.openai.com/v1", desc: "OpenAI 旗舰模型" },
  { provider: "anthropic", model: "claude-sonnet-4-20250514", base_url: "https://api.anthropic.com/v1", desc: "Anthropic 最新模型" },
  { provider: "dashscope", model: "qwen3-max", base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1", desc: "通义千问旗舰模型" },
  { provider: "deepseek", model: "deepseek-chat", base_url: "https://api.deepseek.com/v1", desc: "DeepSeek V3" },
];

export default function AgentModelPage() {
  const [config, setConfig] = useState<AgentModelConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [testing, setTesting] = useState(false);

  const handleTestConnection = async () => {
    setTesting(true);
    try {
      const res = await agentModelApi.test();
      if (res.success) {
        message.success(`连接成功 (${res.latency_ms}ms): ${res.output?.slice(0, 60) || "OK"}`);
      } else {
        message.error(`连接失败: ${res.error || "未知错误"}`);
      }
    } catch {
      message.error("测试请求失败，请先保存配置");
    } finally {
      setTesting(false);
    }
  };
  const [form] = Form.useForm();

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await agentModelApi.get();
      setConfig(data);
      if (data) {
        form.setFieldsValue({
          name: data.name,
          provider: data.provider,
          base_url: data.base_url,
          model_name: data.model_name,
          max_tokens: data.max_tokens,
          temperature: data.temperature,
          params: data.params || {},
        });
      }
    } catch {
      // No config yet
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadConfig(); }, []);

  const handleSubmit = async (values: {
    name: string; provider: string; api_key?: string;
    base_url?: string; model_name: string; max_tokens?: number; temperature?: number;
    params?: Record<string, unknown>;
  }) => {
    setSubmitting(true);
    try {
      await agentModelApi.upsert(values);
      message.success("AI助手模型配置已保存");
      loadConfig();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      message.error(axiosError?.response?.data?.detail || "保存失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    try {
      await agentModelApi.remove();
      message.success("已重置为默认配置");
      setConfig(null);
      form.resetFields();
    } catch {
      message.error("操作失败");
    }
  };

  const applyRecommended = (rec: typeof RECOMMENDED_MODELS[0]) => {
    form.setFieldsValue({
      name: `${rec.model} (Agent)`,
      provider: rec.provider,
      model_name: rec.model,
      base_url: rec.base_url,
      max_tokens: 4096,
      temperature: 0.7,
    });
  };

  if (loading) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>;
  }

  return (
    <div className="page-fade-in" style={{ maxWidth: 720 }}>
      <div className="page-header">
        <div>
          <Title level={2}><RobotOutlined /> AI助手模型配置</Title>
          <Text type="secondary">
            配置 AI 助手使用的大语言模型 API，支持任何 OpenAI 兼容接口
          </Text>
        </div>
      </div>

      {!config && (
        <Alert
          type="info"
          showIcon
          message="尚未配置AI助手模型"
          description={
            <div>
              <Paragraph>请配置AI助手使用的模型API。推荐以下模型：</Paragraph>
              <Space wrap>
                {RECOMMENDED_MODELS.map((rm) => (
                  <Tag
                    key={rm.model}
                    color="blue"
                    style={{ cursor: "pointer" }}
                    onClick={() => applyRecommended(rm)}
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
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ max_tokens: 4096, temperature: 0.7 }}
        >
          <Form.Item name="name" label="配置名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="如：Qwen3-Max Agent" />
          </Form.Item>

          <Form.Item name="provider" label="供应商" rules={[{ required: true, message: "请选择供应商" }]}>
            <Select options={PROVIDERS} placeholder="选择模型供应商" />
          </Form.Item>

          <Form.Item name="model_name" label="模型标识" rules={[{ required: true, message: "请输入模型标识" }]}>
            <Input placeholder="如：gpt-4o, qwen3-max, deepseek-chat" />
          </Form.Item>

          <Form.Item name="api_key" label="API Key" rules={[{ required: !config, message: "请输入API Key" }]}>
            <Input.Password placeholder={config ? "留空保持不变" : "输入 API Key"} />
          </Form.Item>

          <Form.Item name="base_url" label="API 地址 (Base URL)">
            <Input placeholder="如：https://dashscope.aliyuncs.com/compatible-mode/v1" />
          </Form.Item>

          <Form.Item name="max_tokens" label="最大输出 Token 数">
            <InputNumber min={256} max={32768} step={256} style={{ width: "100%" }} />
          </Form.Item>

          <Form.Item name="temperature" label="Temperature (创造性)">
            <Slider min={0} max={2} step={0.1} marks={{ 0: "精确", 0.7: "平衡", 1.5: "创意", 2: "随机" }} />
          </Form.Item>

          <Collapse
            ghost
            items={[{
              key: "params",
              label: <Text type="secondary">更多参数 (top_p, top_k, 重复惩罚)</Text>,
              children: (
                <div>
                  <Form.Item name={["params", "top_p"]} label="Top P (核采样)">
                    <Slider min={0} max={1} step={0.05} marks={{ 0: "0", 0.9: "0.9", 1: "1" }} />
                  </Form.Item>
                  <Form.Item name={["params", "top_k"]} label="Top K">
                    <InputNumber min={1} max={100} style={{ width: "100%" }} placeholder="不设置则使用模型默认值" />
                  </Form.Item>
                  <Form.Item name={["params", "repetition_penalty"]} label="重复惩罚 (Repetition Penalty)">
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
              <Button type="primary" htmlType="submit" loading={submitting} icon={<SaveOutlined />}>
                {config ? "更新配置" : "保存配置"}
              </Button>
              {config && (
                <Button icon={<ApiOutlined />} loading={testing} onClick={handleTestConnection}>
                  测试连接
                </Button>
              )}
              {config && (
                <Popconfirm title="确认重置？将清除当前配置" onConfirm={handleDelete}>
                  <Button danger icon={<DeleteOutlined />}>重置为默认</Button>
                </Popconfirm>
              )}
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {config && (
        <Card style={{ marginTop: 16 }}>
          <Title level={5}>当前配置</Title>
          <Space direction="vertical" size={4}>
            <Text>供应商: <Tag color="blue">{config.provider}</Tag></Text>
            <Text>模型: <Text strong>{config.model_name}</Text></Text>
            <Text>API地址: <Text code>{config.base_url || "(默认)"}</Text></Text>
            <Text>最大Token: {config.max_tokens} | Temperature: {config.temperature}
              {config.params?.top_p != null && ` | Top P: ${config.params.top_p}`}
              {config.params?.top_k != null && ` | Top K: ${config.params.top_k}`}
              {config.params?.repetition_penalty != null && ` | 重复惩罚: ${config.params.repetition_penalty}`}
            </Text>
          </Space>
        </Card>
      )}
    </div>
  );
}
