"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Table, Button, Modal, Form, Input, Select, Upload, Tabs,
  Card, Typography, Tag, Space, Popconfirm, message, Descriptions,
} from "antd";
import {
  PlusOutlined, UploadOutlined, DeleteOutlined, EyeOutlined,
  DatabaseOutlined, BookOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
} from "@ant-design/icons";
import { datasetsApi, benchmarksApi } from "@/lib/api";
import type { Dataset, BuiltinBenchmarkDataset } from "@/types";
import { formatDate } from "@/lib/utils";
import { useDataRefresh } from "@/lib/useDataRefresh";

const { Title, Text } = Typography;

const CATEGORIES = [
  { value: "qa", label: "问答 (QA)" },
  { value: "code", label: "代码生成" },
  { value: "chat", label: "对话评测" },
  { value: "rag", label: "RAG 评测" },
  { value: "safety", label: "安全评测" },
  { value: "benchmark", label: "基准测试" },
  { value: "other", label: "其他" },
];

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [builtinDatasets, setBuiltinDatasets] = useState<BuiltinBenchmarkDataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [builtinLoading, setBuiltinLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [previewModal, setPreviewModal] = useState(false);
  const [previewData, setPreviewData] = useState<{ records: Record<string, unknown>[]; total: number } | null>(null);
  const [previewTitle, setPreviewTitle] = useState("");
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [fileList, setFileList] = useState<unknown[]>([]);

  const loadDatasets = async () => {
    setLoading(true);
    try {
      setDatasets(await datasetsApi.list());
    } finally {
      setLoading(false);
    }
  };

  const loadBuiltinDatasets = async () => {
    setBuiltinLoading(true);
    try {
      setBuiltinDatasets(await datasetsApi.builtinBenchmarks());
    } finally {
      setBuiltinLoading(false);
    }
  };

  useEffect(() => {
    loadDatasets();
    loadBuiltinDatasets();
  }, []);

  useDataRefresh(["datasets"], loadDatasets);

  const handleSubmit = async (values: { name: string; category: string; description?: string; format: string }) => {
    if (!fileList.length) {
      message.error("请选择文件");
      return;
    }
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("name", values.name);
      formData.append("category", values.category);
      formData.append("format", values.format || "jsonl");
      if (values.description) formData.append("description", values.description);
      const file = (fileList[0] as { originFileObj: File }).originFileObj;
      formData.append("file", file);

      await datasetsApi.create(formData);
      message.success("数据集上传成功");
      setModalOpen(false);
      form.resetFields();
      setFileList([]);
      loadDatasets();
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      message.error(axiosError?.response?.data?.detail || "上传失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePreview = async (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setPreviewTitle(dataset.name);
    try {
      const data = await datasetsApi.preview(dataset.id);
      setPreviewData(data);
      setPreviewModal(true);
    } catch {
      message.error("获取预览失败");
    }
  };

  const handleBenchmarkPreview = async (benchmarkId: string, name: string) => {
    setPreviewTitle(name);
    try {
      const data = await benchmarksApi.preview(benchmarkId, 10);
      setPreviewData({ records: data.records, total: data.total });
      setPreviewModal(true);
    } catch {
      message.error("获取预览失败");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await datasetsApi.delete(id);
      message.success("已删除");
      loadDatasets();
    } catch {
      message.error("删除失败");
    }
  };

  const columns = useMemo(() => [
    { title: "名称", dataIndex: "name", key: "name" },
    { title: "类别", dataIndex: "category", key: "category", render: (c: string) => <Tag color="blue">{c}</Tag> },
    { title: "格式", dataIndex: "format", key: "format" },
    { title: "样本数", dataIndex: "size", key: "size" },
    { title: "状态", dataIndex: "status", key: "status", render: (s: string) => <Tag color="success">{s}</Tag> },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", render: formatDate },
    {
      title: "操作", key: "action",
      render: (_: unknown, record: Dataset) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => handlePreview(record)}>预览</Button>
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], []);

  const builtinColumns = useMemo(() => [
    {
      title: "名称", dataIndex: "name", key: "name",
      render: (name: string, record: BuiltinBenchmarkDataset) => (
        <Space>
          <BookOutlined />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: "描述", dataIndex: "description", key: "description",
      ellipsis: true,
      width: 280,
    },
    {
      title: "样本数", dataIndex: "size", key: "size",
      render: (size: number) => size.toLocaleString(),
    },
    {
      title: "评测指标", dataIndex: "metric", key: "metric",
      render: (m: string) => <Tag color="purple">{m}</Tag>,
    },
    {
      title: "分类", dataIndex: "categories", key: "categories",
      render: (cats: string[]) => (
        <Space wrap size={[0, 4]}>
          {cats.slice(0, 3).map((c) => <Tag key={c} color="geekblue">{c}</Tag>)}
          {cats.length > 3 && <Tag>+{cats.length - 3}</Tag>}
        </Space>
      ),
    },
    {
      title: "数据状态", dataIndex: "data_available", key: "data_available",
      render: (available: boolean, record: BuiltinBenchmarkDataset) =>
        available ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            数据已就绪 {record.size.toLocaleString()}条
          </Tag>
        ) : (
          <Tag icon={<ExclamationCircleOutlined />} color="warning">
            仅演示数据
          </Tag>
        ),
    },
    {
      title: "操作", key: "action",
      render: (_: unknown, record: BuiltinBenchmarkDataset) => (
        <Button
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleBenchmarkPreview(record.benchmark_id, record.name)}
        >
          预览
        </Button>
      ),
    },
  ], []);

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <Title level={2}>数据集管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          上传数据集
        </Button>
      </div>

      <Card>
        <Tabs
          defaultActiveKey="my"
          items={[
            {
              key: "my",
              label: (
                <span><DatabaseOutlined /> 我的数据集</span>
              ),
              children: (
                <Table
                  dataSource={datasets}
                  columns={columns}
                  rowKey="id"
                  loading={loading}
                  locale={{ emptyText: "暂无数据集，点击上方按钮上传" }}
                />
              ),
            },
            {
              key: "builtin",
              label: (
                <span><BookOutlined /> 内置基准数据集</span>
              ),
              children: (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <Text type="secondary">
                      系统内置的标准评测基准数据集，可直接用于评测。下载完整数据集后可获得完整评测体验。
                    </Text>
                  </div>
                  <Table
                    dataSource={builtinDatasets}
                    columns={builtinColumns}
                    rowKey="id"
                    loading={builtinLoading}
                    pagination={{ pageSize: 20 }}
                  />
                </>
              ),
            },
          ]}
        />
      </Card>

      <Modal title="上传数据集" open={modalOpen} onCancel={() => { setModalOpen(false); form.resetFields(); setFileList([]); }} footer={null} width={560}>
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 16 }}>
          <Form.Item name="name" label="数据集名称" rules={[{ required: true }]}>
            <Input placeholder="如：GSM8K 数学题-v1" />
          </Form.Item>
          <Form.Item name="category" label="类别" rules={[{ required: true }]}>
            <Select options={CATEGORIES} placeholder="选择数据集类别" />
          </Form.Item>
          <Form.Item name="format" label="格式" initialValue="jsonl">
            <Select options={[
              { value: "jsonl", label: "JSONL" },
              { value: "json", label: "JSON" },
              { value: "csv", label: "CSV" },
              { value: "txt", label: "TXT（每行一条记录）" },
              { value: "zip", label: "ZIP（自动解析内含文件）" },
            ]} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="数据文件" required>
            <Upload
              fileList={fileList as Parameters<typeof Upload>[0]["fileList"]}
              beforeUpload={() => false}
              onChange={({ fileList: fl }) => setFileList(fl)}
              accept=".jsonl,.json,.csv,.txt,.zip"
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>选择文件 (JSONL/JSON/CSV/TXT/ZIP)</Button>
            </Upload>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={submitting}>上传</Button>
              <Button onClick={() => setModalOpen(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`数据预览: ${previewTitle}`}
        open={previewModal}
        onCancel={() => setPreviewModal(false)}
        footer={null}
        width={800}
      >
        {previewData && (
          <div>
            <p className="preview-count">共 {previewData.total.toLocaleString()} 条记录，显示前 {previewData.records.length} 条</p>
            {previewData.records.map((record, i) => (
              <Card key={i} size="small" className="preview-record">
                <pre className="preview-pre">
                  {JSON.stringify(record, null, 2)}
                </pre>
              </Card>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
