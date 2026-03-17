"use client";

import { Suspense, useEffect, useState } from "react";
import {
  Form, Input, Select, Button, Card, Typography, Checkbox, Modal,
  InputNumber, Divider, Alert, Space, message, Steps, Row, Col, Descriptions, Tag, Tooltip, Spin, AutoComplete, Radio, Badge,
} from "antd";
import { QuestionCircleOutlined, ThunderboltOutlined, SafetyCertificateOutlined, ExperimentOutlined, DatabaseOutlined, TrophyOutlined } from "@ant-design/icons";
import { useRouter, useSearchParams } from "next/navigation";
import { modelsApi, datasetsApi, evaluationsApi, benchmarksApi, promptsApi, judgeModelsApi, metricsApi, evalTemplatesApi } from "@/lib/api";
import type { ModelConfig, Dataset, Benchmark, PromptTemplate, JudgeModelConfig, MetricDefinition, EvaluationTemplate } from "@/types";
import { SaveOutlined, FolderOpenOutlined, DeleteOutlined } from "@ant-design/icons";

const { Title, Text } = Typography;

const JUDGE_DIMENSIONS = ["accuracy", "fluency", "relevance", "helpfulness", "safety", "reasoning"];

const STEP_TITLES = ["基本信息", "选择模型", "数据集", "评测配置", "确认提交"];

// Preset evaluation configs for quick start
const EVAL_PRESETS: { label: string; icon: React.ReactNode; desc: string; config: Record<string, unknown> }[] = [
  {
    label: "快速评测",
    icon: <ThunderboltOutlined />,
    desc: "仅评测性能指标和基本质量，速度最快",
    config: { performance: true, cost_analysis: true },
  },
  {
    label: "质量全面评测",
    icon: <ExperimentOutlined />,
    desc: "全面检测幻觉、安全性、一致性、鲁棒性等",
    config: { performance: true, hallucination: true, safety: true, consistency: true, robustness: true, cost_analysis: true },
  },
  {
    label: "安全与合规",
    icon: <SafetyCertificateOutlined />,
    desc: "重点检测安全性、幻觉和指令遵循",
    config: { performance: true, safety: true, hallucination: true, instruction_following: true },
  },
  {
    label: "客观指标评测",
    icon: <ExperimentOutlined />,
    desc: "使用ROUGE/BLEU/METEOR等客观算法指标评估，需参考答案",
    config: { performance: true, objective_metrics: true, selected_metrics: [] },
  },
];

function NewEvaluationPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [form] = Form.useForm();
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [judgeModels, setJudgeModels] = useState<JudgeModelConfig[]>([]);
  const [metricsRegistry, setMetricsRegistry] = useState<MetricDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [llmJudge, setLlmJudge] = useState(false);
  const [domainEval, setDomainEval] = useState(false);
  const [objectiveMetrics, setObjectiveMetrics] = useState(false);
  const [selectedBenchmarks, setSelectedBenchmarks] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [dataSource, setDataSource] = useState<"dataset" | "benchmark">("dataset");
  const [templates, setTemplates] = useState<EvaluationTemplate[]>([]);
  const [saveTemplateModalOpen, setSaveTemplateModalOpen] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDesc, setTemplateDesc] = useState("");
  const [savingTemplate, setSavingTemplate] = useState(false);

  useEffect(() => {
    Promise.all([modelsApi.list(), datasetsApi.list(), benchmarksApi.list(), promptsApi.list(), judgeModelsApi.list(), metricsApi.registry(), evalTemplatesApi.list()])
      .then(([m, d, b, p, jm, mr, tpl]) => {
        setModels(m);
        setDatasets(d);
        setBenchmarks(b);
        setPrompts(p);
        setJudgeModels(jm);
        setMetricsRegistry(mr);
        setTemplates(tpl);

        // Auto-select benchmark from URL param (e.g., /evaluations/new?benchmark=gsm8k)
        const benchmarkParam = searchParams.get("benchmark");
        if (benchmarkParam) {
          const validBenchmark = b.find((bm: Benchmark) => bm.id === benchmarkParam);
          if (validBenchmark) {
            form.setFieldsValue({
              benchmarks: [benchmarkParam],
              name: `${validBenchmark.name} 基准评测`,
            });
            setSelectedBenchmarks([benchmarkParam]);
            setDataSource("benchmark");
            message.info(`已自动选择基准测试: ${validBenchmark.name}`);
          }
        }
      })
      .catch(() => {
        message.error("加载数据失败");
      });
  }, [searchParams, form]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const values = form.getFieldsValue(true);
      const { name, description, model_ids, dataset_id, max_samples, ...evalConfig } = values;
      const task = await evaluationsApi.create({
        name,
        description,
        model_ids,
        dataset_id,
        evaluator_config: {
          ...evalConfig,
          performance: true,
          max_samples: max_samples || undefined,
        },
      });
      message.success("评测任务已创建");
      router.push(`/evaluations/${task.id}`);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      message.error(axiosError?.response?.data?.detail || "创建失败");
    } finally {
      setLoading(false);
    }
  };

  const next = async () => {
    try {
      // Validate current step fields
      if (currentStep === 0) {
        await form.validateFields(["name"]);
      } else if (currentStep === 1) {
        await form.validateFields(["model_ids"]);
      } else if (currentStep === 3) {
        // Validate domain eval config if enabled
        const values = form.getFieldsValue(true);
        if (values.domain_eval) {
          if (!values.dataset_id) {
            message.warning("垂直领域评测需要选择数据集（提供待评测的输入样本）");
            return;
          }
          if (!values.generation_prompt_ids?.length) {
            message.warning("请选择至少一个生成提示词模板");
            return;
          }
          if (!values.evaluation_prompt_ids?.length) {
            message.warning("请选择至少一个评测提示词模板");
            return;
          }
          if (!values.judge_model_id) {
            message.warning("垂直领域评测需要选择裁判模型");
            return;
          }
        }
        if (values.llm_judge && !values.judge_model_id) {
          message.warning("启用 LLM-Judge 需要选择裁判模型");
          return;
        }
      }
      setCurrentStep((s) => s + 1);
    } catch {
      // validation failed
    }
  };

  const prev = () => setCurrentStep((s) => s - 1);

  const loadTemplate = (tpl: EvaluationTemplate) => {
    const { evaluator_config, model_ids, dataset_id } = tpl;
    form.setFieldsValue({
      model_ids,
      dataset_id: dataset_id || undefined,
      ...evaluator_config,
    });
    // Sync local state
    setLlmJudge(!!evaluator_config.llm_judge);
    setDomainEval(!!evaluator_config.domain_eval);
    setObjectiveMetrics(!!evaluator_config.objective_metrics);
    setSelectedBenchmarks((evaluator_config.benchmarks as string[]) || []);
    message.success(`已加载模板「${tpl.name}」`);
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      message.warning("请输入模板名称");
      return;
    }
    setSavingTemplate(true);
    try {
      const values = form.getFieldsValue(true);
      const { name, description, model_ids, dataset_id, max_samples, ...evalConfig } = values;
      const tpl = await evalTemplatesApi.create({
        name: templateName.trim(),
        description: templateDesc.trim() || undefined,
        model_ids: model_ids || [],
        dataset_id: dataset_id || undefined,
        evaluator_config: { ...evalConfig, performance: true, max_samples: max_samples || undefined },
      });
      setTemplates((prev) => [tpl, ...prev]);
      setSaveTemplateModalOpen(false);
      setTemplateName("");
      setTemplateDesc("");
      message.success("模板已保存");
    } catch {
      message.error("保存模板失败");
    } finally {
      setSavingTemplate(false);
    }
  };

  const handleDeleteTemplate = async (id: number, e?: React.MouseEvent) => {
    e?.stopPropagation();
    try {
      await evalTemplatesApi.delete(id);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
      message.success("模板已删除");
    } catch {
      message.error("删除失败");
    }
  };

  const modelMap = Object.fromEntries(models.map((m) => [m.id, m.name]));

  const renderReview = () => {
    const values = form.getFieldsValue(true);
    const selectedModels = (values.model_ids || []).map((id: number) => modelMap[id] || `#${id}`);
    const selectedBenchmarks = values.benchmarks || [];
    const enabledEvals = [
      values.performance && "性能分析",
      values.llm_judge && "LLM-Judge",
      values.hallucination && "幻觉检测",
      values.robustness && "鲁棒性",
      values.consistency && "一致性",
      values.safety && "安全检测",
      values.rag_eval && "RAG评测",
      values.multiturn && "多轮对话",
      values.code_execution && "代码执行",
      values.instruction_following && "指令遵循",
      values.cot_reasoning && "思维链推理",
      values.long_context && "长上下文",
      values.structured_output && "结构化输出",
      values.multilingual && "多语言",
      values.tool_calling && "工具调用",
      values.multimodal && "多模态",
      values.cost_analysis && "性价比",
      values.domain_eval && "垂直领域评测",
      values.objective_metrics && "客观评估指标",
      values.enable_thinking && "思考模式",
    ].filter(Boolean);

    return (
      <Card>
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="任务名称">{values.name || "-"}</Descriptions.Item>
          <Descriptions.Item label="描述">{values.description || "-"}</Descriptions.Item>
          <Descriptions.Item label="评测模型">
            <Space wrap>{selectedModels.map((n: string) => <Tag key={n} color="blue">{n}</Tag>)}</Space>
          </Descriptions.Item>
          <Descriptions.Item label="数据集">
            {values.dataset_id
              ? datasets.find((d) => d.id === values.dataset_id)?.name || "-"
              : selectedBenchmarks.length > 0
                ? "使用内置基准数据集"
                : "未选择"}
          </Descriptions.Item>
          <Descriptions.Item label="最大样本数">{values.max_samples || "全部"}</Descriptions.Item>
          <Descriptions.Item label="基准测试">
            {selectedBenchmarks.length > 0
              ? <Space wrap>{selectedBenchmarks.map((b: string) => <Tag key={b} color="green">{b}</Tag>)}</Space>
              : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="启用评测器">
            <Space wrap>{enabledEvals.map((e) => <Tag key={e as string} color="purple">{e}</Tag>)}</Space>
            {enabledEvals.length === 0 && "-"}
          </Descriptions.Item>
          {values.domain_eval && (
            <>
              <Descriptions.Item label="评测领域">
                <Tag color="cyan">{values.domain || "通用"}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="评测模式">
                {values.eval_mode === "evaluate_optimize" ? "评测 + 优化" : "仅评测"}
              </Descriptions.Item>
            </>
          )}
        </Descriptions>
      </Card>
    );
  };

  return (
    <div className="page-fade-in">
      <Title level={2} style={{ marginBottom: 24 }}>创建评测任务</Title>

      <Steps current={currentStep} style={{ marginBottom: 24 }} items={STEP_TITLES.map((t) => ({ title: t }))} />

      <Form
        form={form}
        layout="vertical"
        initialValues={{ performance: true, hallucination_n_samples: 5, consistency_n_runs: 3 }}
      >
        {/* Step 0: Basic Info */}
        <div style={{ display: currentStep === 0 ? "block" : "none" }}>
          {templates.length > 0 && (
            <Card title={<Space><FolderOpenOutlined />从模板加载</Space>} style={{ marginBottom: 16 }} size="small">
              <Space wrap>
                {templates.map((tpl) => (
                  <Tag
                    key={tpl.id}
                    color="blue"
                    style={{ cursor: "pointer", padding: "4px 12px", fontSize: 13 }}
                    onClick={() => loadTemplate(tpl)}
                    closable
                    onClose={(e) => { e.preventDefault(); handleDeleteTemplate(tpl.id); }}
                  >
                    {tpl.name}
                  </Tag>
                ))}
              </Space>
              {templates.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>点击标签加载对应的评测配置，点击 x 删除模板</Text>
                </div>
              )}
            </Card>
          )}
          <Card title="基本信息">
            <Form.Item name="name" label="任务名称" rules={[{ required: true, message: "请输入任务名称" }]}>
              <Input placeholder="如：GPT-4o vs Claude-3.5 数学能力对比" />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <Input.TextArea rows={2} placeholder="评测任务的详细描述（可选）" />
            </Form.Item>
          </Card>
        </div>

        {/* Step 1: Models */}
        <div style={{ display: currentStep === 1 ? "block" : "none" }}>
          <Card title="选择评测模型">
            <Form.Item name="model_ids" label="评测模型" rules={[{ required: true, message: "至少选择一个模型" }]}>
              <Select
                mode="multiple"
                placeholder="选择要评测的模型（支持多选对比）"
                options={models.map((m) => ({ value: m.id, label: `${m.name} (${m.model_name})` }))}
                size="large"
              />
            </Form.Item>
            <Text type="secondary">选择多个模型可进行横向对比评测，结果将自动生成对比图表。</Text>
          </Card>
        </div>

        {/* Step 2: Dataset */}
        <div style={{ display: currentStep === 2 ? "block" : "none" }}>
          <Card title="数据集配置">
            <div style={{ marginBottom: 16 }}>
              <Radio.Group
                value={dataSource}
                onChange={(e) => {
                  setDataSource(e.target.value);
                  if (e.target.value === "dataset") {
                    // 切换到自定义数据集时，清空基准选择
                    form.setFieldsValue({ benchmarks: [] });
                    setSelectedBenchmarks([]);
                  } else {
                    // 切换到内置基准时，清空数据集选择
                    form.setFieldsValue({ dataset_id: undefined });
                  }
                }}
                optionType="button"
                buttonStyle="solid"
                size="large"
              >
                <Radio.Button value="dataset"><DatabaseOutlined /> 评测数据集</Radio.Button>
                <Radio.Button value="benchmark"><TrophyOutlined /> 内置基准数据集 <Badge count={benchmarks.length} style={{ marginLeft: 4, backgroundColor: dataSource === "benchmark" ? "#fff" : "#1677ff", color: dataSource === "benchmark" ? "#1677ff" : "#fff" }} size="small" /></Radio.Button>
              </Radio.Group>
            </div>

            {dataSource === "dataset" && (
              <>
                <Form.Item name="dataset_id" label="评测数据集">
                  <Select
                    allowClear
                    placeholder="选择已上传的数据集"
                    options={datasets.map((d) => ({ value: d.id, label: `${d.name} (${d.size} 条 · ${d.category})` }))}
                    size="large"
                  />
                </Form.Item>
                <Alert type="info" message="如果不选择数据集，可切换到「内置基准数据集」使用标准基准测试。" showIcon />
              </>
            )}

            {dataSource === "benchmark" && (
              <>
                <Form.Item name="benchmarks" label="选择基准测试">
                  <Checkbox.Group
                    onChange={(vals) => setSelectedBenchmarks(vals as string[])}
                  >
                    <Row gutter={[8, 8]}>
                      {benchmarks.map((b) => (
                        <Col xs={24} sm={12} lg={8} key={b.id}>
                          <Card
                            size="small"
                            hoverable
                            style={{
                              border: selectedBenchmarks.includes(b.id)
                                ? "2px solid var(--primary, #1677ff)"
                                : "1px solid #f0f0f0",
                              background: selectedBenchmarks.includes(b.id) ? "#f0f5ff" : undefined,
                            }}
                          >
                            <Checkbox value={b.id} style={{ width: "100%" }}>
                              <div>
                                <Text strong>{b.name}</Text>
                                <br />
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  {b.description?.slice(0, 40) || b.metric} · {b.sample_size || "?"} 样本
                                </Text>
                                <br />
                                <Tag color="green" style={{ marginTop: 4, fontSize: 11 }}>{b.metric}</Tag>
                                {b.data_available ? (
                                  <Tag color="blue" style={{ fontSize: 11 }}>数据就绪</Tag>
                                ) : (
                                  <Tag color="orange" style={{ fontSize: 11 }}>需下载</Tag>
                                )}
                              </div>
                            </Checkbox>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  </Checkbox.Group>
                </Form.Item>
                {selectedBenchmarks.length > 0 && (
                  <Alert
                    type="success"
                    showIcon
                    message={`已选择 ${selectedBenchmarks.length} 个基准测试: ${selectedBenchmarks.join(", ")}`}
                    style={{ marginTop: 8 }}
                  />
                )}
                {selectedBenchmarks.length === 0 && (
                  <Alert type="warning" message="请至少选择一个基准测试" showIcon style={{ marginTop: 8 }} />
                )}
                {selectedBenchmarks.some((b) => b.startsWith("healthbench")) && (
                  <Alert
                    type="warning"
                    showIcon
                    style={{ marginTop: 8 }}
                    message="HealthBench 需要在评测配置步骤中配置独立裁判模型"
                  />
                )}
              </>
            )}

            <Divider />
            <Form.Item name="max_samples" label="最大样本数">
              <InputNumber min={1} max={10000} placeholder="留空使用全部" style={{ width: "100%" }} />
            </Form.Item>
          </Card>
        </div>

        {/* Step 3: Evaluator Config */}
        <div style={{ display: currentStep === 3 ? "block" : "none" }}>
          {/* Quick Presets */}
          <Card title="快速配置" size="small" style={{ marginBottom: 16 }}>
            <Space wrap>
              {EVAL_PRESETS.map((preset) => (
                <Tooltip key={preset.label} title={preset.desc}>
                  <Button
                    icon={preset.icon}
                    onClick={() => {
                      // Reset all eval dimensions first
                      const resetFields: Record<string, boolean> = {};
                      ["hallucination", "robustness", "consistency", "safety", "rag_eval", "multiturn",
                       "code_execution", "instruction_following", "cot_reasoning", "long_context",
                       "structured_output", "multilingual", "tool_calling", "multimodal", "cost_analysis",
                       "objective_metrics",
                      ].forEach((k) => { resetFields[k] = false; });
                      form.setFieldsValue({ ...resetFields, ...preset.config });
                      setObjectiveMetrics(!!preset.config.objective_metrics);
                      setLlmJudge(!!preset.config.llm_judge);
                      setDomainEval(!!preset.config.domain_eval);
                      message.success(`已应用「${preset.label}」配置`);
                    }}
                  >
                    {preset.label}
                  </Button>
                </Tooltip>
              ))}
            </Space>
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">选择一个预设配置快速开始，或在下方自定义评测维度</Text>
            </div>
          </Card>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="基础评测" size="small">
                <Form.Item name="performance" valuePropName="checked">
                  <Checkbox defaultChecked>性能分析（延迟、吞吐量、成本）</Checkbox>
                </Form.Item>
                <Form.Item name="enable_thinking" valuePropName="checked">
                  <Checkbox>
                    启用思考模式
                    <Tooltip title="开启后模型会进行深度思考再回答（如 Qwen3、DeepSeek-R1 等支持的模型），关闭则直接输出答案。默认关闭。"><QuestionCircleOutlined style={{ marginLeft: 4, color: "var(--text-tertiary)" }} /></Tooltip>
                  </Checkbox>
                </Form.Item>
                <Form.Item name="llm_judge" valuePropName="checked">
                  <Checkbox onChange={(e) => setLlmJudge(e.target.checked)}>
                    LLM-as-Judge 评分
                    <Tooltip title="使用另一个强力模型作为裁判，对被测模型的回答进行多维度打分"><QuestionCircleOutlined style={{ marginLeft: 4, color: "var(--text-tertiary)" }} /></Tooltip>
                  </Checkbox>
                </Form.Item>
                {llmJudge && (
                  <div style={{ paddingLeft: 24 }}>
                    <Form.Item name="judge_model_id" label="裁判模型">
                      <Select
                        placeholder={judgeModels.length > 0 ? "选择裁判模型" : "请先在「裁判模型」页面添加"}
                        options={judgeModels.filter((jm) => jm.is_active).map((jm) => ({
                          value: jm.id,
                          label: `${jm.name} (${jm.model_name})${jm.is_default ? " [默认]" : ""}`,
                        }))}
                        notFoundContent={
                          <div style={{ padding: 8, textAlign: "center" }}>
                            <Text type="secondary">暂无裁判模型</Text>
                            <br />
                            <a href="/settings/judge-models" target="_blank" rel="noreferrer">
                              前往配置裁判模型
                            </a>
                          </div>
                        }
                      />
                    </Form.Item>
                    <Form.Item name="judge_dimensions" label="评测维度">
                      <Select mode="multiple" options={JUDGE_DIMENSIONS.map((d) => ({ value: d, label: d }))} defaultValue={["accuracy", "fluency", "relevance"]} />
                    </Form.Item>
                  </div>
                )}
              </Card>

              <Card title="客观评估指标" size="small" style={{ marginTop: 16, border: objectiveMetrics ? "1px solid var(--primary)" : undefined }}>
                <Form.Item name="objective_metrics" valuePropName="checked">
                  <Checkbox onChange={(e) => setObjectiveMetrics(e.target.checked)}>
                    启用客观评估指标
                    <Tooltip title="使用ROUGE/BLEU/METEOR等标准NLP算法指标进行客观评估"><QuestionCircleOutlined style={{ marginLeft: 4, color: "var(--text-tertiary)" }} /></Tooltip>
                  </Checkbox>
                </Form.Item>
                {objectiveMetrics && (
                  <div style={{ paddingLeft: 24 }}>
                    {(() => {
                      const categories = Array.from(new Set(metricsRegistry.map((m) => m.category)));
                      return categories.map((cat) => {
                        const catMetrics = metricsRegistry.filter((m) => m.category === cat);
                        const catLabel = catMetrics[0]?.category_label || cat;
                        return (
                          <div key={cat} style={{ marginBottom: 12 }}>
                            <Text strong style={{ fontSize: 13 }}>{catLabel}：</Text>
                            <div style={{ paddingLeft: 8, marginTop: 4 }}>
                              <Form.Item name="selected_metrics" valuePropName="value" noStyle>
                                <Checkbox.Group>
                                  <Row gutter={[4, 2]}>
                                    {catMetrics.map((m) => (
                                      <Col key={m.id} span={12}>
                                        <Checkbox value={m.id}>
                                          {m.name}
                                          {m.heavy && <Tag color="orange" style={{ marginLeft: 4, fontSize: 11, lineHeight: "16px", padding: "0 4px" }}>较慢</Tag>}
                                          {m.needs_reference && <Tooltip title="需要参考答案"><Tag color="blue" style={{ marginLeft: 2, fontSize: 11, lineHeight: "16px", padding: "0 4px" }}>需参考</Tag></Tooltip>}
                                        </Checkbox>
                                      </Col>
                                    ))}
                                  </Row>
                                </Checkbox.Group>
                              </Form.Item>
                            </div>
                          </div>
                        );
                      });
                    })()}
                    <Alert
                      type="info"
                      showIcon
                      style={{ marginTop: 8 }}
                      message="不选择任何指标 = 自动使用全部轻量级指标。标「需参考」的指标在无参考答案时自动跳过。"
                    />
                  </div>
                )}
              </Card>

              <Card title="标准基准测试" size="small" style={{ marginTop: 16 }}>
                <Form.Item name="benchmarks" label="选择基准集">
                  <Checkbox.Group
                    options={benchmarks.map((b) => ({ value: b.id, label: `${b.name} (${b.metric})` }))}
                    onChange={(vals) => setSelectedBenchmarks(vals as string[])}
                  />
                </Form.Item>
                {selectedBenchmarks.some((b) => b.startsWith("healthbench")) && (
                  <>
                    <Alert
                      type="warning"
                      showIcon
                      style={{ marginTop: 8 }}
                      message="HealthBench 需要独立裁判模型"
                      description={
                        <div>
                          <p style={{ margin: "4px 0" }}>
                            标准 HealthBench 评测流程：<strong>被测模型</strong>生成回复 → <strong>独立裁判模型</strong>（如 GPT-4o）逐条评判医生标注的评分标准（Rubric）。
                          </p>
                          <p style={{ margin: "4px 0", color: "#cf1322" }}>
                            如不配置裁判模型，将退化为模型自评（不推荐，结果不可靠）。
                          </p>
                        </div>
                      }
                    />
                    <Form.Item name="judge_model_id" label="裁判模型（用于 HealthBench Rubric 评分）" style={{ marginTop: 12 }}>
                      <Select
                        placeholder={judgeModels.length > 0 ? "选择裁判模型（强烈推荐）" : "请先在「裁判模型」页面添加"}
                        options={judgeModels.filter((jm) => jm.is_active).map((jm) => ({
                          value: jm.id,
                          label: `${jm.name} (${jm.model_name})${jm.is_default ? " [默认]" : ""}`,
                        }))}
                        notFoundContent={
                          <div style={{ padding: 8, textAlign: "center" }}>
                            <Text type="secondary">暂无裁判模型</Text>
                            <br />
                            <a href="/settings/judge-models" target="_blank" rel="noreferrer">
                              前往配置裁判模型 →
                            </a>
                          </div>
                        }
                        allowClear
                      />
                    </Form.Item>
                    <Alert
                      type="info"
                      showIcon
                      style={{ marginTop: 4 }}
                      message="HealthBench 医疗健康评测"
                      description={
                        <div>
                          <p style={{ margin: "4px 0" }}>
                            基于 OpenAI 发布的医疗 LLM 评测基准，由 262 位医生标注，使用多轮对话 + 医生评分标准（Rubric）进行评测。
                          </p>
                          <p style={{ margin: "4px 0" }}>
                            <strong>7 大主题：</strong>
                            <Space size={[4, 4]} wrap style={{ marginLeft: 4 }}>
                              <Tag color="blue">全球健康</Tag><Tag color="blue">急诊转诊</Tag>
                              <Tag color="blue">不确定性应对</Tag><Tag color="blue">专业沟通</Tag>
                              <Tag color="blue">上下文获取</Tag><Tag color="blue">健康数据</Tag>
                              <Tag color="blue">回复深度</Tag>
                            </Space>
                          </p>
                          <p style={{ margin: "4px 0" }}>
                            <strong>5 个维度：</strong>
                            <Space size={[4, 4]} wrap style={{ marginLeft: 4 }}>
                              <Tag color="green">完整性</Tag><Tag color="green">准确性</Tag>
                              <Tag color="green">上下文感知</Tag><Tag color="green">沟通质量</Tag>
                              <Tag color="green">指令遵循</Tag>
                            </Space>
                          </p>
                        </div>
                      }
                    />
                  </>
                )}
              </Card>
            </Col>

            <Col xs={24} lg={12}>
              <Card title="垂直领域评测" size="small" style={{ marginBottom: 16, border: domainEval ? "1px solid var(--primary)" : undefined }}>
                <Form.Item name="domain_eval" valuePropName="checked">
                  <Checkbox onChange={(e) => setDomainEval(e.target.checked)}>启用垂直领域评测（双Prompt模式）</Checkbox>
                </Form.Item>
                {domainEval && (
                  <div style={{ paddingLeft: 24 }}>
                    <Form.Item name="domain" label="领域">
                      <AutoComplete
                        placeholder="选择预设或输入自定义领域"
                        options={[
                          { value: "medical", label: "医疗健康" },
                          { value: "finance", label: "金融" },
                          { value: "industrial", label: "工业" },
                          { value: "legal", label: "法律" },
                          { value: "education", label: "教育" },
                          { value: "general", label: "通用" },
                        ]}
                        filterOption={(input, option) =>
                          (option?.label ?? "").toString().toLowerCase().includes(input.toLowerCase()) ||
                          (option?.value ?? "").toString().toLowerCase().includes(input.toLowerCase())
                        }
                      />
                    </Form.Item>
                    <Form.Item name="generation_prompt_ids" label="生成提示词（给被测模型）">
                      <Select
                        mode="multiple"
                        placeholder="选择生成提示词模板"
                        options={prompts.filter((p) => p.prompt_type === "generation").map((p) => ({ value: p.id, label: `${p.name}${p.domain ? ` [${p.domain}]` : ""}` }))}
                      />
                    </Form.Item>
                    <Form.Item name="evaluation_prompt_ids" label="评测提示词（给上位评判模型）">
                      <Select
                        mode="multiple"
                        placeholder="选择评测提示词模板"
                        options={prompts.filter((p) => p.prompt_type === "evaluation").map((p) => ({ value: p.id, label: `${p.name}${p.domain ? ` [${p.domain}]` : ""}` }))}
                      />
                    </Form.Item>
                    <Form.Item name="judge_model_id" label="上位评判模型">
                      <Select
                        placeholder={judgeModels.length > 0 ? "选择评判模型" : "请先在「裁判模型」页面添加"}
                        options={judgeModels.filter((jm) => jm.is_active).map((jm) => ({
                          value: jm.id,
                          label: `${jm.name} (${jm.model_name})${jm.is_default ? " [默认]" : ""}`,
                        }))}
                        notFoundContent={
                          <div style={{ padding: 8, textAlign: "center" }}>
                            <Text type="secondary">暂无裁判模型</Text>
                            <br />
                            <a href="/settings/judge-models" target="_blank" rel="noreferrer">
                              前往配置裁判模型
                            </a>
                          </div>
                        }
                      />
                    </Form.Item>
                    <Form.Item name="eval_mode" label="评测模式" initialValue="evaluate">
                      <Select options={[
                        { value: "evaluate", label: "仅评测" },
                        { value: "evaluate_optimize", label: "评测 + 优化（可诊断并生成训练数据）" },
                      ]} />
                    </Form.Item>
                    <Alert type="info" showIcon message="双Prompt模式：生成提示词发送给被测模型生成回答，评测提示词发送给上位模型进行打分和诊断。" style={{ marginTop: 4 }} />
                  </div>
                )}
              </Card>

              <Card title="高级评测维度" size="small">
                <Row gutter={[8, 4]}>
                  <Col span={12}><Form.Item name="hallucination" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>幻觉检测 <Tooltip title="检测模型是否生成了不符合事实的内容"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="robustness" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>鲁棒性测试 <Tooltip title="用变换后的输入测试模型输出是否稳定"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="consistency" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>自洽性评测 <Tooltip title="多次询问同一问题，检测回答是否一致"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="safety" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>安全/毒性检测 <Tooltip title="检测模型是否输出有害、偏见或违规内容"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="rag_eval" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>RAG 专项评测 <Tooltip title="评测检索增强生成能力：引用准确性、上下文忠实度"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="multiturn" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>多轮对话评测 <Tooltip title="测试多轮对话中的上下文记忆和连贯性"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="code_execution" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>代码执行验证 <Tooltip title="实际执行模型生成的代码并验证正确性"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                </Row>
              </Card>

              <Card title="扩展评测维度" size="small" style={{ marginTop: 16 }}>
                <Row gutter={[8, 4]}>
                  <Col span={12}><Form.Item name="instruction_following" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>指令遵循 <Tooltip title="测试模型是否严格遵循指令要求（如格式、字数限制等）"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="cot_reasoning" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>思维链推理 <Tooltip title="评测模型的逐步推理能力和逻辑链质量"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="long_context" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>长上下文 <Tooltip title="Needle-in-a-Haystack 测试，评估长文本中的信息提取能力"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="structured_output" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>结构化输出 <Tooltip title="验证模型是否能生成符合 JSON Schema 等格式要求的输出"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="multilingual" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>多语言评测 <Tooltip title="在多种语言下测试模型能力"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="tool_calling" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>工具调用 <Tooltip title="测试模型是否能正确选择和调用工具/函数"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="multimodal" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>多模态评测 <Tooltip title="测试模型处理图片、文档等多模态输入的能力"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                  <Col span={12}><Form.Item name="cost_analysis" valuePropName="checked" style={{ marginBottom: 4 }}><Checkbox>性价比分析 <Tooltip title="计算每个token的成本和质量性价比"><QuestionCircleOutlined style={{ color: "var(--text-tertiary)", fontSize: 12 }} /></Tooltip></Checkbox></Form.Item></Col>
                </Row>
              </Card>
            </Col>
          </Row>
        </div>

        {/* Step 4: Review */}
        <div style={{ display: currentStep === 4 ? "block" : "none" }}>
          {renderReview()}
          <div style={{ marginTop: 16, display: "flex", gap: 12 }}>
            <Alert
              type="info"
              showIcon
              message="提示"
              description="评测任务将异步执行，您可以在任务列表查看实时进度。启用越多评测器，运行时间越长。"
              style={{ flex: 1 }}
            />
            <Button
              icon={<SaveOutlined />}
              onClick={() => setSaveTemplateModalOpen(true)}
              style={{ height: "auto", minHeight: 60 }}
            >
              保存为模板
            </Button>
          </div>
        </div>
      </Form>

      {/* Save Template Modal */}
      <Modal
        title="保存评测模板"
        open={saveTemplateModalOpen}
        onCancel={() => setSaveTemplateModalOpen(false)}
        onOk={handleSaveTemplate}
        confirmLoading={savingTemplate}
        okText="保存"
      >
        <div style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 12 }}>
            <Text strong>模板名称</Text>
            <Input
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              placeholder="如：标准质量评测、数学能力对比..."
              style={{ marginTop: 4 }}
            />
          </div>
          <div>
            <Text strong>描述（可选）</Text>
            <Input.TextArea
              value={templateDesc}
              onChange={(e) => setTemplateDesc(e.target.value)}
              placeholder="模板用途说明..."
              rows={2}
              style={{ marginTop: 4 }}
            />
          </div>
          <Alert
            type="info"
            showIcon
            message="模板将保存当前选择的模型、数据集和所有评测配置，下次创建评测时可一键加载。"
            style={{ marginTop: 12 }}
          />
        </div>
      </Modal>

      {/* Navigation Buttons */}
      <div style={{ marginTop: 24, display: "flex", justifyContent: "space-between" }}>
        <Button size="large" onClick={() => currentStep > 0 ? prev() : router.push("/evaluations")}>
          {currentStep > 0 ? "上一步" : "取消"}
        </Button>
        <Space>
          {currentStep < STEP_TITLES.length - 1 && (
            <Button type="primary" size="large" onClick={next}>下一步</Button>
          )}
          {currentStep === STEP_TITLES.length - 1 && (
            <Button type="primary" size="large" loading={loading} onClick={handleSubmit}>
              创建评测任务
            </Button>
          )}
        </Space>
      </div>
    </div>
  );
}

export default function NewEvaluationPage() {
  return (
    <Suspense fallback={<Spin size="large" style={{ display: "flex", justifyContent: "center", marginTop: 100 }} />}>
      <NewEvaluationPageInner />
    </Suspense>
  );
}
