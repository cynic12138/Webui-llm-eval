"use client";

import { useEffect, useState } from "react";
import { Card, Row, Col, Typography, Tag, Button, Skeleton, Modal, message } from "antd";
import {
  BookOutlined, ArrowRightOutlined, EyeOutlined,
  CheckCircleOutlined, ExclamationCircleOutlined,
} from "@ant-design/icons";
import { benchmarksApi } from "@/lib/api";
import type { Benchmark } from "@/types";
import Link from "next/link";

const { Title, Text, Paragraph } = Typography;

const BENCHMARK_COLORS: Record<string, string> = {
  mmlu_pro: "blue",
  gsm8k: "green",
  humaneval: "purple",
  ceval: "red",
  hellaswag: "orange",
  truthfulqa: "cyan",
  math: "magenta",
  arc: "gold",
  mt_bench: "lime",
  alpaca_eval: "geekblue",
  ifeval: "volcano",
  swe_bench: "#2db7f5",
  bigcodebench: "#87d068",
  livebench: "#108ee9",
  healthbench: "#f50",
  healthbench_hard: "#f50",
  healthbench_consensus: "#f50",
};

export default function BenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [previewModal, setPreviewModal] = useState(false);
  const [previewData, setPreviewData] = useState<{ records: Record<string, unknown>[]; total: number } | null>(null);
  const [previewTitle, setPreviewTitle] = useState("");

  useEffect(() => {
    benchmarksApi.list().then(setBenchmarks).finally(() => setLoading(false));
  }, []);

  const handlePreview = async (benchmarkId: string, name: string) => {
    setPreviewTitle(name);
    try {
      const data = await benchmarksApi.preview(benchmarkId, 10);
      setPreviewData({ records: data.records, total: data.total });
      setPreviewModal(true);
    } catch {
      message.error("获取预览失败");
    }
  };

  if (loading) {
    return (
      <div className="skeleton-page">
        <Skeleton active paragraph={{ rows: 0 }} />
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Col xs={24} sm={12} lg={8} key={i}>
              <Card><Skeleton active paragraph={{ rows: 4 }} /></Card>
            </Col>
          ))}
        </Row>
      </div>
    );
  }

  return (
    <div className="page-fade-in">
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ marginBottom: 8 }}>标准基准测试</Title>
        <Text type="secondary">
          内置标准评测基准集，无需额外配置即可评测模型能力。运行下载脚本可获取完整数据集。
        </Text>
      </div>

      <Row gutter={[16, 16]}>
        {benchmarks.map((b) => (
          <Col xs={24} sm={12} lg={8} key={b.id}>
            <Card
              hoverable
              style={{ height: "100%" }}
              actions={[
                <Button
                  key="preview"
                  type="link"
                  icon={<EyeOutlined />}
                  onClick={() => handlePreview(b.id, b.name)}
                >
                  预览数据
                </Button>,
                <Link href={`/evaluations/new?benchmark=${b.id}`} key="eval">
                  <Button type="link" icon={<ArrowRightOutlined />}>开始评测</Button>
                </Link>,
              ]}
            >
              <div className="benchmark-card-header">
                <BookOutlined />
                <Title level={4} style={{ margin: 0 }}>{b.name}</Title>
              </div>
              <Paragraph type="secondary" style={{ marginBottom: 12 }}>{b.description}</Paragraph>
              <div className="benchmark-card-tags">
                <Tag color={BENCHMARK_COLORS[b.id] || "default"}>指标: {b.metric}</Tag>
                {b.data_available ? (
                  <Tag icon={<CheckCircleOutlined />} color="success">
                    数据已就绪 {(b.actual_sample_count || b.sample_size).toLocaleString()}条
                  </Tag>
                ) : (
                  <Tag icon={<ExclamationCircleOutlined />} color="warning">
                    仅演示数据
                  </Tag>
                )}
                {b.categories.map((c) => (
                  <Tag key={c} color="geekblue">{c}</Tag>
                ))}
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card style={{ marginTop: 24 }} title="如何使用基准测试">
        <ol className="benchmark-guide">
          <li>添加您的模型配置（Models 页面）</li>
          <li>进入 创建评测 页面</li>
          <li>在 评测器配置 中勾选需要的基准测试</li>
          <li>无需上传数据集，系统将自动加载内置基准数据</li>
          <li>启动评测后查看各基准得分对比</li>
        </ol>
        <div style={{ marginTop: 16, padding: "12px 16px", background: "#f6f8fa", borderRadius: 6 }}>
          <Text type="secondary">
            <strong>下载完整数据集：</strong>运行 <code>python eval_engine/benchmark_data/download_benchmarks.py</code> 可从 HuggingFace 下载全部基准的真实数据集。
            支持 <code>--benchmarks mmlu_pro,gsm8k</code> 指定下载、<code>--max-samples 500</code> 限制样本数。
          </Text>
        </div>
      </Card>

      <Modal
        title={`数据预览: ${previewTitle}`}
        open={previewModal}
        onCancel={() => setPreviewModal(false)}
        footer={null}
        width={800}
      >
        {previewData && (
          <div>
            <p style={{ color: "#666", marginBottom: 12 }}>
              共 {previewData.total.toLocaleString()} 条记录，显示前 {previewData.records.length} 条
            </p>
            {previewData.records.map((record, i) => (
              <Card key={i} size="small" style={{ marginBottom: 8 }}>
                <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12, maxHeight: 200, overflow: "auto" }}>
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
