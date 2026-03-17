"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Card, Button, Select, Input, Form, Typography, Table, Space, message, Spin, Tag,
} from "antd";
import { PlayCircleOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import { promptsApi, modelsApi } from "@/lib/api";
import type { PromptTemplate, PromptExperiment, ModelConfig } from "@/types";
import Link from "next/link";

const { Title, Text } = Typography;
const { TextArea } = Input;

export default function ExperimentPage() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [experiment, setExperiment] = useState<PromptExperiment | null>(null);
  const [form] = Form.useForm();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [tpls, mdls] = await Promise.all([
        promptsApi.list(),
        modelsApi.list(),
      ]);
      setTemplates(tpls);
      setModels(mdls);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRun = useCallback(async (values: {
    name: string;
    template_ids: number[];
    model_ids: number[];
    test_inputs_raw: string;
  }) => {
    setRunning(true);
    setExperiment(null);
    try {
      // Parse test inputs: each line is a JSON object
      let testInputs: Record<string, unknown>[] = [];
      if (values.test_inputs_raw && values.test_inputs_raw.trim()) {
        const lines = values.test_inputs_raw.trim().split("\n");
        for (const line of lines) {
          if (line.trim()) {
            testInputs.push(JSON.parse(line.trim()));
          }
        }
      }

      const created = await promptsApi.createExperiment({
        name: values.name,
        template_ids: values.template_ids,
        model_ids: values.model_ids,
        test_inputs: testInputs,
      });

      message.info("实验已创建，正在运行...");
      const result = await promptsApi.runExperiment(created.id);
      setExperiment(result);
      message.success("实验完成！");
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } }; message?: string };
      message.error(axiosError?.response?.data?.detail || axiosError?.message || "实验运行失败");
    } finally {
      setRunning(false);
    }
  }, []);

  // Build result table from experiment results
  const buildResultData = useCallback(() => {
    if (!experiment?.results) return [];
    const results = experiment.results as Record<string, Record<string, Array<{
      input?: Record<string, unknown>;
      rendered_prompt?: string;
      output?: string;
      error?: string;
      latency_ms?: number;
    }>>>;

    const rows: Array<{
      key: string;
      template_name: string;
      template_id: string;
      model_name: string;
      model_id: string;
      input_index: number;
      rendered_prompt: string;
      output: string;
      latency_ms: number;
    }> = [];

    for (const [tid, modelResults] of Object.entries(results)) {
      const tpl = templates.find((t) => t.id === Number(tid));
      for (const [mid, outputs] of Object.entries(modelResults)) {
        const mdl = models.find((m) => m.id === Number(mid));
        outputs.forEach((item, idx) => {
          rows.push({
            key: `${tid}-${mid}-${idx}`,
            template_name: tpl?.name || `Template ${tid}`,
            template_id: tid,
            model_name: mdl?.name || `Model ${mid}`,
            model_id: mid,
            input_index: idx,
            rendered_prompt: item.rendered_prompt || "",
            output: item.error || item.output || "",
            latency_ms: item.latency_ms || 0,
          });
        });
      }
    }
    return rows;
  }, [experiment, templates, models]);

  const resultColumns = [
    { title: "模板", dataIndex: "template_name", key: "template_name", width: 140 },
    { title: "模型", dataIndex: "model_name", key: "model_name", width: 140 },
    { title: "#", dataIndex: "input_index", key: "input_index", width: 50 },
    {
      title: "渲染后的提示词", dataIndex: "rendered_prompt", key: "rendered_prompt",
      ellipsis: true, width: 250,
    },
    {
      title: "输出", dataIndex: "output", key: "output",
      ellipsis: true,
    },
    {
      title: "延迟(ms)", dataIndex: "latency_ms", key: "latency_ms", width: 100,
      render: (v: number) => <Tag color={v < 2000 ? "green" : v < 5000 ? "orange" : "red"}>{v}</Tag>,
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: "center", marginTop: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <Space>
          <Link href="/prompts">
            <Button icon={<ArrowLeftOutlined />}>返回模板列表</Button>
          </Link>
          <Title level={2} style={{ margin: 0 }}>提示词 A/B 实验</Title>
        </Space>
      </div>

      <Card style={{ marginBottom: 24 }}>
        <Form form={form} layout="vertical" onFinish={handleRun}>
          <Form.Item name="name" label="实验名称" rules={[{ required: true, message: "请输入实验名称" }]}>
            <Input placeholder="如：产品描述 A/B 测试" />
          </Form.Item>

          <Form.Item name="template_ids" label="选择模板" rules={[{ required: true, message: "请选择至少一个模板" }]}>
            <Select
              mode="multiple"
              placeholder="选择要对比的提示词模板"
              options={templates.map((t) => ({ value: t.id, label: `${t.name} (v${t.version})` }))}
            />
          </Form.Item>

          <Form.Item name="model_ids" label="选择模型" rules={[{ required: true, message: "请选择至少一个模型" }]}>
            <Select
              mode="multiple"
              placeholder="选择要测试的模型"
              options={models.map((m) => ({ value: m.id, label: `${m.name} (${m.model_name})` }))}
            />
          </Form.Item>

          <Form.Item name="test_inputs_raw" label="测试输入（每行一个 JSON 对象）">
            <TextArea
              rows={4}
              placeholder={'每行一个 JSON 对象，如：\n{"product_name": "智能手表", "tone": "专业"}\n{"product_name": "耳机", "tone": "活泼"}'}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<PlayCircleOutlined />}
              loading={running}
              size="large"
            >
              {running ? "运行中..." : "运行实验"}
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {experiment && experiment.results && (
        <Card title="实验结果">
          <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
            实验状态: <Tag color={experiment.status === "completed" ? "success" : "processing"}>{experiment.status}</Tag>
          </Text>
          <Table
            dataSource={buildResultData()}
            columns={resultColumns}
            rowKey="key"
            scroll={{ x: 900 }}
            pagination={{ pageSize: 20 }}
          />
        </Card>
      )}
    </div>
  );
}
