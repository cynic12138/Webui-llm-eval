"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Card, Typography, Button, Space, Tag, message, Alert,
  Row, Col, Checkbox, Input, Spin, Empty,
} from "antd";
import { ThunderboltOutlined, ExportOutlined, CheckOutlined, ArrowLeftOutlined, BarChartOutlined } from "@ant-design/icons";
import Link from "next/link";
import { evaluationsApi } from "@/lib/api";
import type { EvaluationTask, GeneratedTrainingData } from "@/types";

const { Title, Text } = Typography;
const { TextArea } = Input;

export default function OptimizePage() {
  const { id } = useParams();
  const router = useRouter();
  const [task, setTask] = useState<EvaluationTask | null>(null);
  const [data, setData] = useState<GeneratedTrainingData[]>([]);
  const [loading, setLoading] = useState(true);
  const [diagnosing, setDiagnosing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [editedOutputs, setEditedOutputs] = useState<Record<number, string>>({});
  const [exportName, setExportName] = useState("");

  const taskId = Number(id);

  const loadData = async () => {
    try {
      const [t, d] = await Promise.all([
        evaluationsApi.get(taskId),
        evaluationsApi.getGeneratedData(taskId),
      ]);
      setTask(t);
      setData(d);
      setSelectedIds(new Set(d.filter((x) => x.is_approved).map((x) => x.id)));
    } catch {
      message.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [id]);

  const handleDiagnose = async () => {
    setDiagnosing(true);
    try {
      const res = await evaluationsApi.diagnose(taskId);
      message.success(`诊断完成: ${res.count} 个低分样本`);
    } catch {
      message.error("诊断失败");
    } finally {
      setDiagnosing(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await evaluationsApi.generateData(taskId);
      message.success(`已生成 ${res.count} 条优化数据`);
      loadData();
    } catch {
      message.error("生成失败");
    } finally {
      setGenerating(false);
    }
  };

  const handleToggle = (itemId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) next.delete(itemId);
      else next.add(itemId);
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedIds.size === data.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(data.map((d) => d.id)));
    }
  };

  const handleSaveEdit = async (item: GeneratedTrainingData) => {
    const newOutput = editedOutputs[item.id];
    if (!newOutput || newOutput === item.corrected_output) return;
    try {
      await evaluationsApi.updateGeneratedData(taskId, item.id, {
        corrected_output: newOutput,
        is_edited: true,
      });
      message.success("已保存");
      loadData();
    } catch {
      message.error("保存失败");
    }
  };

  const handleApprove = async (item: GeneratedTrainingData) => {
    try {
      await evaluationsApi.updateGeneratedData(taskId, item.id, {
        is_approved: !item.is_approved,
      });
      loadData();
    } catch {
      message.error("操作失败");
    }
  };

  const handleExport = async () => {
    if (!exportName.trim()) {
      message.error("请输入数据集名称");
      return;
    }
    if (selectedIds.size === 0) {
      message.error("请至少选择一条数据");
      return;
    }
    setExporting(true);
    try {
      const dataset = await evaluationsApi.exportDataset(taskId, Array.from(selectedIds), exportName.trim());
      message.success(`数据集 "${dataset.name}" 已导出`);
      router.push("/datasets");
    } catch {
      message.error("导出失败");
    } finally {
      setExporting(false);
    }
  };

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spin size="large" /></div>;
  if (!task) return <Alert type="error" message="任务不存在" />;

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <Space>
          <Link href={`/evaluations/${id}`}>
            <Button icon={<ArrowLeftOutlined />} type="text" />
          </Link>
          <Title level={2} style={{ margin: 0 }}>评测优化: {task.name}</Title>
        </Space>
        <Space>
          <Link href={`/results/${id}`}>
            <Button icon={<BarChartOutlined />}>查看评测结果</Button>
          </Link>
          <Button icon={<ThunderboltOutlined />} loading={diagnosing} onClick={handleDiagnose}>
            诊断低分样本
          </Button>
          <Button type="primary" loading={generating} onClick={handleGenerate}>
            生成优化数据
          </Button>
        </Space>
      </div>

      {/* Step-by-step flow guide */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space size="large" wrap>
          <div style={{ textAlign: "center" }}>
            <Tag color={data.length > 0 ? "success" : diagnosing ? "processing" : "default"}>步骤 1</Tag>
            <div style={{ fontSize: 12, marginTop: 4 }}>诊断低分样本</div>
          </div>
          <span style={{ color: "var(--text-tertiary)" }}>→</span>
          <div style={{ textAlign: "center" }}>
            <Tag color={data.length > 0 ? "success" : generating ? "processing" : "default"}>步骤 2</Tag>
            <div style={{ fontSize: 12, marginTop: 4 }}>生成修正数据</div>
          </div>
          <span style={{ color: "var(--text-tertiary)" }}>→</span>
          <div style={{ textAlign: "center" }}>
            <Tag color={data.some((d) => d.is_approved) ? "success" : "default"}>步骤 3</Tag>
            <div style={{ fontSize: 12, marginTop: 4 }}>审核并编辑</div>
          </div>
          <span style={{ color: "var(--text-tertiary)" }}>→</span>
          <div style={{ textAlign: "center" }}>
            <Tag color="default">步骤 4</Tag>
            <div style={{ fontSize: 12, marginTop: 4 }}>导出新数据集</div>
          </div>
        </Space>
      </Card>

      {data.length > 0 && (
        <Row gutter={12} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small" style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 600 }}>{data.length}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>生成数据总数</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 600, color: "#52c41a" }}>{data.filter((d) => d.is_approved).length}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>已审核通过</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 600, color: "#fa8c16" }}>{data.filter((d) => d.is_edited).length}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>已手动编辑</div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ textAlign: "center" }}>
              <div style={{ fontSize: 24, fontWeight: 600 }}>{selectedIds.size}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>已选择导出</div>
            </Card>
          </Col>
        </Row>
      )}

      {data.length === 0 ? (
        <Card>
          <Empty
            description={
              <div>
                <p>暂无优化数据</p>
                <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  请按照以上步骤操作：先点击「诊断低分样本」分析问题，再点击「生成优化数据」生成修正版回答
                </p>
              </div>
            }
          />
        </Card>
      ) : (
        <>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Row align="middle" justify="space-between">
              <Col>
                <Space>
                  <Checkbox
                    checked={selectedIds.size === data.length}
                    indeterminate={selectedIds.size > 0 && selectedIds.size < data.length}
                    onChange={handleSelectAll}
                  >
                    全选 ({selectedIds.size}/{data.length})
                  </Checkbox>
                  <Text type="secondary">选择要导出的优化数据</Text>
                  <Button
                    size="small"
                    type="link"
                    onClick={async () => {
                      const unapproved = data.filter((d) => !d.is_approved);
                      if (unapproved.length === 0) { message.info("所有数据已审核"); return; }
                      try {
                        await Promise.all(unapproved.map((d) =>
                          evaluationsApi.updateGeneratedData(taskId, d.id, { is_approved: true })
                        ));
                        message.success(`已批量审核 ${unapproved.length} 条数据`);
                        loadData();
                      } catch { message.error("批量审核失败"); }
                    }}
                  >
                    全部审核通过
                  </Button>
                </Space>
              </Col>
              <Col>
                <Space>
                  <Input
                    placeholder="新数据集名称"
                    value={exportName}
                    onChange={(e) => setExportName(e.target.value)}
                    style={{ width: 220 }}
                  />
                  <Button
                    type="primary"
                    icon={<ExportOutlined />}
                    loading={exporting}
                    onClick={handleExport}
                    disabled={selectedIds.size === 0}
                  >
                    导出为新数据集 ({selectedIds.size})
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>

          {data.map((item) => (
            <Card
              key={item.id}
              size="small"
              style={{ marginBottom: 12, borderLeft: selectedIds.has(item.id) ? "3px solid var(--primary)" : undefined }}
            >
              <Row gutter={16}>
                <Col xs={24} md={11}>
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      <Checkbox checked={selectedIds.has(item.id)} onChange={() => handleToggle(item.id)} />
                      <strong>原始输入</strong>
                    </Space>
                    <div style={{ background: "#f5f5f5", padding: 8, borderRadius: 6, marginTop: 4, maxHeight: 150, overflow: "auto", whiteSpace: "pre-wrap", fontSize: 13 }}>
                      {item.original_input || "-"}
                    </div>
                  </div>
                  <div>
                    <strong>原始输出</strong>
                    <Tag color="error" style={{ marginLeft: 8 }}>需优化</Tag>
                    <div style={{ background: "#fef2f2", padding: 8, borderRadius: 6, marginTop: 4, maxHeight: 150, overflow: "auto", whiteSpace: "pre-wrap", fontSize: 13 }}>
                      {item.original_output || "-"}
                    </div>
                  </div>
                </Col>
                <Col xs={24} md={13}>
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      <strong>修正版输出</strong>
                      {item.is_edited && <Tag color="orange">已编辑</Tag>}
                      {item.is_approved && <Tag color="success">已审核</Tag>}
                    </Space>
                    <TextArea
                      rows={6}
                      value={editedOutputs[item.id] ?? item.corrected_output ?? ""}
                      onChange={(e) => setEditedOutputs((prev) => ({ ...prev, [item.id]: e.target.value }))}
                      style={{ marginTop: 4, fontSize: 13 }}
                    />
                    <Space style={{ marginTop: 8 }}>
                      <Button size="small" onClick={() => handleSaveEdit(item)} disabled={!editedOutputs[item.id] || editedOutputs[item.id] === item.corrected_output}>
                        保存编辑
                      </Button>
                      <Button
                        size="small"
                        type={item.is_approved ? "default" : "primary"}
                        icon={<CheckOutlined />}
                        onClick={() => handleApprove(item)}
                      >
                        {item.is_approved ? "取消审核" : "审核通过"}
                      </Button>
                    </Space>
                  </div>
                  {item.improvement_notes && (
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                      <strong>改进说明：</strong>{item.improvement_notes}
                    </div>
                  )}
                </Col>
              </Row>
            </Card>
          ))}
        </>
      )}
    </div>
  );
}
