"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Card,
  Typography, Tag, Space, Popconfirm, message, Row, Col, AutoComplete,
} from "antd";
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { promptsApi } from "@/lib/api";
import type { PromptTemplate } from "@/types";
import { formatDate, truncate } from "@/lib/utils";
import { useDataRefresh } from "@/lib/useDataRefresh";
import Link from "next/link";

const { Title } = Typography;
const { TextArea } = Input;

const PROMPT_TYPES = [
  { value: "generation", label: "生成提示词" },
  { value: "evaluation", label: "评测提示词" },
];

const PRESET_DOMAINS = [
  { value: "medical", label: "医疗健康" },
  { value: "finance", label: "金融" },
  { value: "industrial", label: "工业" },
  { value: "legal", label: "法律" },
  { value: "education", label: "教育" },
  { value: "general", label: "通用" },
];

export default function PromptsPage() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [filterType, setFilterType] = useState<string | undefined>();
  const [filterDomain, setFilterDomain] = useState<string | undefined>();

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      setTemplates(await promptsApi.list(filterType, filterDomain));
    } finally {
      setLoading(false);
    }
  }, [filterType, filterDomain]);

  useEffect(() => { loadTemplates(); }, [loadTemplates]);

  useDataRefresh(["prompts"], loadTemplates);

  const handleSubmit = useCallback(async (values: {
    name: string; content: string; variables?: string; tags?: string;
    prompt_type?: string; domain?: string;
  }) => {
    setSubmitting(true);
    try {
      const variables = values.variables
        ? values.variables.split(",").map((v) => v.trim()).filter(Boolean)
        : [];
      const tags = values.tags
        ? values.tags.split(",").map((t) => t.trim()).filter(Boolean)
        : [];

      if (editingTemplate) {
        await promptsApi.update(editingTemplate.id, {
          name: values.name,
          content: values.content,
          variables,
          tags,
          prompt_type: values.prompt_type,
          domain: values.domain,
        });
        message.success("模板更新成功");
      } else {
        await promptsApi.create({
          name: values.name,
          content: values.content,
          variables,
          tags,
          prompt_type: values.prompt_type || "generation",
          domain: values.domain,
        });
        message.success("模板创建成功");
      }
      setModalOpen(false);
      form.resetFields();
      setEditingTemplate(null);
      loadTemplates();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      message.error(axiosError?.response?.data?.detail || "操作失败");
    } finally {
      setSubmitting(false);
    }
  }, [editingTemplate, form, loadTemplates]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await promptsApi.delete(id);
      message.success("已删除");
      loadTemplates();
    } catch {
      message.error("删除失败");
    }
  }, [loadTemplates]);

  const openEdit = useCallback((template: PromptTemplate) => {
    setEditingTemplate(template);
    form.setFieldsValue({
      name: template.name,
      content: template.content,
      variables: (template.variables || []).join(", "),
      tags: (template.tags || []).join(", "),
      prompt_type: template.prompt_type || "generation",
      domain: template.domain,
    });
    setModalOpen(true);
  }, [form]);

  const columns = useMemo(() => [
    {
      title: "名称", dataIndex: "name", key: "name",
      render: (name: string) => <strong>{name}</strong>,
    },
    {
      title: "类型", dataIndex: "prompt_type", key: "prompt_type", width: 100,
      render: (t: string) => <Tag color={t === "evaluation" ? "orange" : "blue"}>{t === "evaluation" ? "评测" : "生成"}</Tag>,
    },
    {
      title: "领域", dataIndex: "domain", key: "domain", width: 90,
      render: (d: string) => d ? <Tag color="cyan">{PRESET_DOMAINS.find((x) => x.value === d)?.label || d}</Tag> : "-",
    },
    {
      title: "内容预览", dataIndex: "content", key: "content",
      render: (content: string) => <span>{truncate(content, 50)}</span>,
    },
    {
      title: "变量", dataIndex: "variables", key: "variables",
      render: (vars: string[]) => (
        <Space wrap>
          {(vars || []).map((v) => <Tag key={v} color="blue">{v}</Tag>)}
        </Space>
      ),
    },
    { title: "版本", dataIndex: "version", key: "version", width: 70 },
    {
      title: "标签", dataIndex: "tags", key: "tags",
      render: (tags: string[]) => (
        <Space wrap>
          {(tags || []).map((t) => <Tag key={t}>{t}</Tag>)}
        </Space>
      ),
    },
    {
      title: "状态", dataIndex: "is_active", key: "is_active", width: 80,
      render: (v: boolean) => <Tag color={v ? "success" : "default"}>{v ? "启用" : "禁用"}</Tag>,
    },
    {
      title: "创建时间", dataIndex: "created_at", key: "created_at",
      render: formatDate, width: 160,
    },
    {
      title: "操作", key: "action", width: 160,
      render: (_: unknown, record: PromptTemplate) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], [openEdit, handleDelete]);

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <Title level={2}>提示词工程</Title>
        <Space>
          <Link href="/prompts/experiment">
            <Button icon={<ExperimentOutlined />}>A/B 实验</Button>
          </Link>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingTemplate(null); form.resetFields(); setModalOpen(true); }}>
            创建模板
          </Button>
        </Space>
      </div>

      <Card>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col>
            <Select
              allowClear
              placeholder="提示词类型"
              style={{ width: 140 }}
              options={PROMPT_TYPES}
              value={filterType}
              onChange={(v) => setFilterType(v)}
            />
          </Col>
          <Col>
            <Select
              allowClear
              placeholder="领域"
              style={{ width: 140 }}
              options={PRESET_DOMAINS}
              value={filterDomain}
              onChange={(v) => setFilterDomain(v)}
            />
          </Col>
        </Row>
        <Table dataSource={templates} columns={columns} rowKey="id" loading={loading} />
      </Card>

      <Modal
        title={editingTemplate ? "编辑模板" : "创建模板"}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingTemplate(null); form.resetFields(); }}
        footer={null}
        width={640}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 16 }}>
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: "请输入模板名称" }]}>
            <Input placeholder="如：产品描述生成器" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="prompt_type" label="提示词类型" initialValue="generation">
                <Select options={PROMPT_TYPES} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="domain" label="领域">
                <AutoComplete
                  allowClear
                  placeholder="选择预设或输入自定义领域"
                  options={PRESET_DOMAINS}
                  filterOption={(input, option) =>
                    (option?.label ?? "").toLowerCase().includes(input.toLowerCase()) ||
                    (option?.value ?? "").toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="content" label="提示词内容" rules={[{ required: true, message: "请输入提示词内容" }]}>
            <TextArea
              rows={6}
              placeholder={"使用 {{变量名}} 定义变量，例如：\n生成提示词用 {{input}} 作为输入\n评测提示词用 {{input}} 和 {{output}} 注入待评测内容"}
            />
          </Form.Item>
          <Form.Item name="variables" label="变量（逗号分隔）">
            <Input placeholder="如：input, output" />
          </Form.Item>
          <Form.Item name="tags" label="标签（逗号分隔）">
            <Input placeholder="如：医疗, 评测, GPT-4" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={submitting}>
                {editingTemplate ? "更新" : "创建"}
              </Button>
              <Button onClick={() => setModalOpen(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
