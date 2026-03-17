"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Card, Alert, Result,
  Typography, Tag, Space, Popconfirm, message, Divider, Tooltip, Steps,
  Collapse, Slider, InputNumber, Row, Col,
} from "antd";
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  RobotOutlined, ExperimentOutlined, CloudOutlined, SettingOutlined,
  CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined,
  ApiOutlined, ThunderboltOutlined, LinkOutlined, PlayCircleOutlined,
  TagsOutlined, SearchOutlined, FilterOutlined,
} from "@ant-design/icons";
import { modelsApi } from "@/lib/api";
import type { ModelConfig } from "@/types";
import { formatDate } from "@/lib/utils";
import { useDataRefresh } from "@/lib/useDataRefresh";

const { Title, Text, Paragraph } = Typography;

const PROVIDERS = [
  { value: "openai", label: "OpenAI", icon: "🤖", defaultUrl: "https://api.openai.com/v1", needsApiKey: true },
  { value: "anthropic", label: "Anthropic", icon: "🧠", defaultUrl: "", needsApiKey: true },
  { value: "deepseek", label: "DeepSeek", icon: "🔍", defaultUrl: "https://api.deepseek.com/v1", needsApiKey: true },
  { value: "dashscope", label: "阿里 DashScope", icon: "☁️", defaultUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", needsApiKey: true },
  { value: "zhipu", label: "智谱 GLM", icon: "🔮", defaultUrl: "https://open.bigmodel.cn/api/paas/v4", needsApiKey: true },
  { value: "vllm", label: "vLLM (本地部署)", icon: "⚡", defaultUrl: "http://localhost:8080/v1", needsApiKey: false },
  { value: "sglang", label: "SGLang (本地部署)", icon: "🚀", defaultUrl: "http://localhost:30000/v1", needsApiKey: false },
  { value: "ollama", label: "Ollama (本地部署)", icon: "🦙", defaultUrl: "http://localhost:11434/v1", needsApiKey: false },
  { value: "azure", label: "Azure OpenAI", icon: "☁️", defaultUrl: "", needsApiKey: true },
  { value: "custom", label: "自定义 (OpenAI 兼容)", icon: "🔧", defaultUrl: "", needsApiKey: false },
];

const PROVIDER_MAP = Object.fromEntries(PROVIDERS.map((p) => [p.value, p]));

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  openai: <RobotOutlined style={{ color: "#4f6ef7" }} />,
  anthropic: <ExperimentOutlined style={{ color: "#7c5cf7" }} />,
  azure: <CloudOutlined style={{ color: "#13c2c2" }} />,
  deepseek: <ApiOutlined style={{ color: "#1677ff" }} />,
  dashscope: <CloudOutlined style={{ color: "#ff6a00" }} />,
  zhipu: <ThunderboltOutlined style={{ color: "#722ed1" }} />,
  vllm: <ThunderboltOutlined style={{ color: "#52c41a" }} />,
  sglang: <ThunderboltOutlined style={{ color: "#eb2f96" }} />,
  ollama: <RobotOutlined style={{ color: "#faad14" }} />,
  custom: <SettingOutlined style={{ color: "#fa8c16" }} />,
};

const TAG_COLORS = [
  "blue", "green", "orange", "purple", "cyan", "magenta", "red", "geekblue", "lime", "gold",
];

function getTagColor(tag: string): string {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) hash = tag.charCodeAt(i) + ((hash << 5) - hash);
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length];
}

// Quick-fill model presets
const MODEL_PRESETS: Record<string, { label: string; model_name: string; base_url?: string }[]> = {
  openai: [
    { label: "GPT-4o", model_name: "gpt-4o" },
    { label: "GPT-4o-mini", model_name: "gpt-4o-mini" },
    { label: "GPT-4-Turbo", model_name: "gpt-4-turbo" },
    { label: "o1-preview", model_name: "o1-preview" },
  ],
  anthropic: [
    { label: "Claude 4 Sonnet", model_name: "claude-sonnet-4-20250514" },
    { label: "Claude 3.5 Sonnet", model_name: "claude-3-5-sonnet-20241022" },
    { label: "Claude 3.5 Haiku", model_name: "claude-3-5-haiku-20241022" },
  ],
  deepseek: [
    { label: "DeepSeek Chat", model_name: "deepseek-chat" },
    { label: "DeepSeek Reasoner", model_name: "deepseek-reasoner" },
  ],
  dashscope: [
    { label: "Qwen-Max", model_name: "qwen-max" },
    { label: "Qwen-Plus", model_name: "qwen-plus" },
    { label: "Qwen-Turbo", model_name: "qwen-turbo" },
  ],
  zhipu: [
    { label: "GLM-4-Plus", model_name: "glm-4-plus" },
    { label: "GLM-4", model_name: "glm-4" },
    { label: "GLM-4-Flash", model_name: "glm-4-flash" },
  ],
};

interface TestResult {
  success: boolean;
  latency_ms?: number;
  output?: string;
  model?: string;
  error?: string;
}

export default function ModelsPage() {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<ModelConfig | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [testingModelId, setTestingModelId] = useState<number | null>(null);
  const [filterTag, setFilterTag] = useState<string>("");
  const [searchText, setSearchText] = useState("");

  const loadModels = useCallback(async () => {
    setLoading(true);
    try {
      setModels(await modelsApi.list());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadModels(); }, [loadModels]);

  useDataRefresh(["models"], loadModels);

  // Collect all unique tags for the filter
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    models.forEach((m) => m.tags?.forEach((t) => tagSet.add(t)));
    return Array.from(tagSet).sort();
  }, [models]);

  const filteredModels = useMemo(() => {
    let result = models;
    if (filterTag) {
      result = result.filter((m) => m.tags?.includes(filterTag));
    }
    if (searchText.trim()) {
      const kw = searchText.trim().toLowerCase();
      result = result.filter((m) =>
        m.name.toLowerCase().includes(kw) ||
        m.model_name.toLowerCase().includes(kw) ||
        m.tags?.some((t) => t.toLowerCase().includes(kw))
      );
    }
    return result;
  }, [models, filterTag, searchText]);

  const handleProviderChange = useCallback((value: string) => {
    setSelectedProvider(value);
    const providerInfo = PROVIDER_MAP[value];
    if (providerInfo?.defaultUrl) {
      form.setFieldValue("base_url", providerInfo.defaultUrl);
    }
    form.setFieldValue("model_name", undefined);
    setTestResult(null);
  }, [form]);

  const handlePresetClick = useCallback((preset: { model_name: string; base_url?: string }) => {
    form.setFieldValue("model_name", preset.model_name);
    if (preset.base_url) {
      form.setFieldValue("base_url", preset.base_url);
    }
  }, [form]);

  const handleTestConnection = useCallback(async () => {
    const values = form.getFieldsValue();
    if (!values.model_name) {
      message.warning("请先填写模型名称");
      return;
    }
    if (!values.base_url && values.provider !== "anthropic") {
      message.warning("请先填写 Base URL");
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const result = await modelsApi.testConnection({
        provider: values.provider,
        api_key: values.api_key || "",
        base_url: values.base_url || "",
        model_name: values.model_name,
      });
      setTestResult(result);
      if (result.success) {
        message.success(`连接成功！延迟 ${result.latency_ms}ms`);
      } else {
        message.error(`连接失败: ${result.error}`);
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } }; message?: string };
      setTestResult({ success: false, error: axiosError?.response?.data?.detail || axiosError?.message || "测试请求失败" });
    } finally {
      setTesting(false);
    }
  }, [form]);

  const handleTestSavedModel = useCallback(async (modelId: number) => {
    setTestingModelId(modelId);
    try {
      const result = await modelsApi.testSaved(modelId);
      if (result.success) {
        message.success(`连接成功！延迟 ${result.latency_ms}ms，回复: "${result.output}"`);
      } else {
        message.error(`连接失败: ${result.error}`);
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } }; message?: string };
      message.error(axiosError?.response?.data?.detail || "测试请求失败");
    } finally {
      setTestingModelId(null);
    }
  }, []);

  const handleSubmit = useCallback(async (values: {
    name: string; provider: string; api_key?: string;
    base_url?: string; model_name: string; params?: Record<string, unknown>;
    tags?: string[];
  }) => {
    setSubmitting(true);
    try {
      if (editingModel) {
        await modelsApi.update(editingModel.id, values);
        message.success("模型更新成功");
      } else {
        await modelsApi.create(values);
        message.success("模型添加成功");
      }
      setModalOpen(false);
      form.resetFields();
      setEditingModel(null);
      setTestResult(null);
      setSelectedProvider("");
      loadModels();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      message.error(axiosError?.response?.data?.detail || "操作失败");
    } finally {
      setSubmitting(false);
    }
  }, [editingModel, form, loadModels]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await modelsApi.delete(id);
      message.success("已删除");
      loadModels();
    } catch {
      message.error("删除失败");
    }
  }, [loadModels]);

  const openEdit = useCallback((model: ModelConfig) => {
    setEditingModel(model);
    setSelectedProvider(model.provider);
    form.setFieldsValue({ ...model, api_key: "", tags: model.tags || [] });
    setTestResult(null);
    setModalOpen(true);
  }, [form]);

  const openCreate = useCallback(() => {
    setEditingModel(null);
    setSelectedProvider("");
    form.resetFields();
    setTestResult(null);
    setModalOpen(true);
  }, [form]);

  const columns = useMemo(() => [
    {
      title: "名称", dataIndex: "name", key: "name",
      render: (name: string, record: ModelConfig) => (
        <Space direction="vertical" size={2}>
          <Space>
            {PROVIDER_ICONS[record.provider.toLowerCase()] || <RobotOutlined />}
            <strong>{name}</strong>
          </Space>
          {record.tags && record.tags.length > 0 && (
            <Space size={2} wrap>
              {record.tags.map((t) => (
                <Tag
                  key={t}
                  color={getTagColor(t)}
                  style={{ fontSize: 11, cursor: "pointer", margin: 0 }}
                  onClick={() => setFilterTag(t)}
                >
                  {t}
                </Tag>
              ))}
            </Space>
          )}
        </Space>
      ),
    },
    {
      title: "提供商", dataIndex: "provider", key: "provider",
      render: (p: string) => {
        const info = PROVIDER_MAP[p];
        return <Tag>{info ? `${info.icon} ${info.label}` : p}</Tag>;
      },
    },
    { title: "模型名称", dataIndex: "model_name", key: "model_name", render: (v: string) => <code>{v}</code> },
    {
      title: "API 端点", dataIndex: "base_url", key: "base_url",
      render: (u: string) => u ? (
        <Tooltip title={u}>
          <Tag icon={<LinkOutlined />} color="blue">{u.replace(/^https?:\/\//, "").slice(0, 30)}{u.length > 40 ? "..." : ""}</Tag>
        </Tooltip>
      ) : <Tag color="default">默认</Tag>,
    },
    {
      title: "状态", dataIndex: "is_active", key: "is_active",
      render: (v: boolean) => <Tag color={v ? "success" : "default"}>{v ? "启用" : "禁用"}</Tag>,
    },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", render: formatDate },
    {
      title: "操作", key: "action", width: 280,
      render: (_: unknown, record: ModelConfig) => (
        <Space>
          <Tooltip title="测试连接">
            <Button
              size="small"
              icon={testingModelId === record.id ? <LoadingOutlined /> : <PlayCircleOutlined />}
              loading={testingModelId === record.id}
              onClick={() => handleTestSavedModel(record.id)}
            >
              测试
            </Button>
          </Tooltip>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], [openEdit, handleDelete, handleTestSavedModel, testingModelId]);

  const providerInfo = PROVIDER_MAP[selectedProvider];
  const presets = selectedProvider ? MODEL_PRESETS[selectedProvider] : undefined;

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <div>
          <Title level={2}>模型管理</Title>
          <Text type="secondary">添加和管理评测使用的 LLM 模型，支持本地部署 (vLLM/SGLang/Ollama) 和云端 API</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} size="large" onClick={openCreate}>
          添加模型
        </Button>
      </div>

      <Card>
        {/* Filter bar */}
        <Row gutter={12} style={{ marginBottom: 16 }} align="middle">
          <Col flex="auto">
            <Input
              placeholder="搜索模型名称、模型ID或标签..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
          <Col>
            <Select
              style={{ minWidth: 160 }}
              value={filterTag}
              onChange={setFilterTag}
              placeholder="按标签筛选"
              allowClear
              suffixIcon={<TagsOutlined />}
              options={[
                { value: "", label: "全部标签" },
                ...allTags.map((t) => ({ value: t, label: t })),
              ]}
            />
          </Col>
        </Row>

        {/* Active tag filter indicator */}
        {filterTag && (
          <div style={{ marginBottom: 12 }}>
            <Space>
              <FilterOutlined style={{ color: "#4f6ef7" }} />
              <Text type="secondary">筛选标签：</Text>
              <Tag color={getTagColor(filterTag)} closable onClose={() => setFilterTag("")}>
                {filterTag}
              </Tag>
              <Text type="secondary">({filteredModels.length} 个模型)</Text>
            </Space>
          </div>
        )}

        <Table dataSource={filteredModels} columns={columns} rowKey="id" loading={loading} />
      </Card>

      <Modal
        title={editingModel ? "编辑模型" : "添加模型"}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingModel(null); form.resetFields(); setTestResult(null); setSelectedProvider(""); }}
        footer={null}
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 16 }}>
          {/* Step 1: Provider */}
          <Form.Item
            name="provider"
            label={<span style={{ fontWeight: 600, fontSize: 15 }}>选择提供商</span>}
            rules={[{ required: true, message: "请选择提供商" }]}
          >
            <Select
              placeholder="选择模型提供商 / 部署方式"
              onChange={handleProviderChange}
              options={PROVIDERS.map((p) => ({
                value: p.value,
                label: (
                  <Space>
                    <span>{p.icon}</span>
                    <span>{p.label}</span>
                    {!p.needsApiKey && <Tag color="green" style={{ fontSize: 10 }}>本地</Tag>}
                  </Space>
                ),
              }))}
              size="large"
            />
          </Form.Item>

          {/* Step 2: Base URL */}
          <Form.Item
            name="base_url"
            label={
              <Space>
                <span style={{ fontWeight: 600, fontSize: 15 }}>API 端点地址 (Base URL)</span>
                {selectedProvider !== "anthropic" && <Tag color="red">必填</Tag>}
              </Space>
            }
            rules={selectedProvider === "anthropic" ? [] : [{ required: true, message: "请输入 API 端点地址" }]}
            help={
              providerInfo
                ? selectedProvider === "anthropic"
                  ? "Anthropic 使用官方 SDK，无需填写 Base URL"
                  : `默认: ${providerInfo.defaultUrl || "请填写您的服务端点"}`
                : "如 http://localhost:8080/v1 (vLLM) 或 https://api.openai.com/v1"
            }
          >
            <Input
              placeholder={
                providerInfo?.defaultUrl
                  ? providerInfo.defaultUrl
                  : "http://your-server:port/v1"
              }
              size="large"
              disabled={selectedProvider === "anthropic"}
              addonBefore={<LinkOutlined />}
            />
          </Form.Item>

          {/* Step 3: Model name */}
          <Form.Item
            name="model_name"
            label={<span style={{ fontWeight: 600, fontSize: 15 }}>模型名称</span>}
            rules={[{ required: true, message: "请输入模型名称" }]}
            help="本地部署时需与部署时的模型名称一致"
          >
            <Input
              placeholder={
                selectedProvider === "vllm" || selectedProvider === "sglang"
                  ? "如: Qwen/Qwen2.5-72B-Instruct"
                  : "如: gpt-4o, claude-3-5-sonnet-20241022"
              }
              size="large"
            />
          </Form.Item>

          {/* Quick presets */}
          {presets && presets.length > 0 && (
            <div style={{ marginBottom: 16, marginTop: -8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>快速选择：</Text>{" "}
              {presets.map((p) => (
                <Tag
                  key={p.model_name}
                  color="blue"
                  style={{ cursor: "pointer", marginBottom: 4 }}
                  onClick={() => handlePresetClick(p)}
                >
                  {p.label}
                </Tag>
              ))}
            </div>
          )}

          {/* Step 4: API Key */}
          <Form.Item
            name="api_key"
            label={
              <Space>
                <span style={{ fontWeight: 600 }}>API Key</span>
                {providerInfo && !providerInfo.needsApiKey && <Tag color="green">本地部署可不填</Tag>}
              </Space>
            }
            rules={providerInfo?.needsApiKey ? [{ required: !editingModel, message: "此提供商需要 API Key" }] : []}
          >
            <Input.Password
              placeholder={
                editingModel
                  ? "留空保持不变"
                  : providerInfo?.needsApiKey
                    ? "请输入 API Key (必填)"
                    : "本地部署可留空，或填写 'EMPTY'"
              }
            />
          </Form.Item>

          {/* Step 5: Display name */}
          <Form.Item
            name="name"
            label="显示名称"
            rules={[{ required: true, message: "请输入显示名称" }]}
            help="用于在评测列表中展示的名称"
          >
            <Input placeholder="如：GPT-4o 生产环境 / 本地 Qwen2.5-72B" />
          </Form.Item>

          {/* Step 6: Tags */}
          <Form.Item
            name="tags"
            label={
              <Space>
                <TagsOutlined />
                <span style={{ fontWeight: 600 }}>标签 (分组)</span>
              </Space>
            }
            help="输入标签后按回车添加，用于分组筛选模型"
          >
            <Select
              mode="tags"
              placeholder="如：生产环境、实验、本地部署、72B..."
              tokenSeparators={[","]}
              options={allTags.map((t) => ({ value: t, label: t }))}
            />
          </Form.Item>

          {/* Advanced Parameters */}
          <Collapse
            ghost
            items={[{
              key: "params",
              label: <Text type="secondary">高级参数 (temperature, top_p, top_k, 重复惩罚等)</Text>,
              children: (
                <div>
                  <Form.Item name={["params", "temperature"]} label="Temperature (创造性)">
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

          <Divider style={{ margin: "16px 0" }} />

          {/* Test Connection */}
          <div style={{ marginBottom: 16 }}>
            <Button
              type="dashed"
              icon={testing ? <LoadingOutlined /> : <PlayCircleOutlined />}
              loading={testing}
              onClick={handleTestConnection}
              block
              size="large"
              style={{ borderColor: testResult?.success ? "#52c41a" : testResult?.success === false ? "#ff4d4f" : undefined }}
            >
              {testing ? "正在测试连接..." : "测试连接"}
            </Button>

            {testResult && (
              <div style={{ marginTop: 12 }}>
                {testResult.success ? (
                  <Alert
                    type="success"
                    showIcon
                    icon={<CheckCircleOutlined />}
                    message={`连接成功！延迟 ${testResult.latency_ms}ms`}
                    description={
                      <div>
                        <div>模型: <code>{testResult.model}</code></div>
                        <div>回复: <Text code>{testResult.output}</Text></div>
                      </div>
                    }
                  />
                ) : (
                  <Alert
                    type="error"
                    showIcon
                    icon={<CloseCircleOutlined />}
                    message="连接失败"
                    description={testResult.error}
                  />
                )}
              </div>
            )}
          </div>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space style={{ width: "100%", justifyContent: "flex-end" }}>
              <Button onClick={() => setModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={submitting} size="large">
                {editingModel ? "更新模型" : "添加模型"}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
