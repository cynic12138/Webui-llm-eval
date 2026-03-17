"use client";

import { useState, useEffect } from "react";
import { Card, Input, Button, Select, Row, Col, Typography, Tag, message, Divider, Space, Spin, Table } from "antd";
import { ThunderboltOutlined, TrophyOutlined } from "@ant-design/icons";
import { modelsApi, arenaApi } from "@/lib/api";
import type { ModelConfig, ArenaMatch } from "@/types";

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

export default function ArenaPage() {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [modelA, setModelA] = useState<number>();
  const [modelB, setModelB] = useState<number>();
  const [prompt, setPrompt] = useState("");
  const [match, setMatch] = useState<ArenaMatch | null>(null);
  const [loading, setLoading] = useState(false);
  const [voting, setVoting] = useState(false);
  const [history, setHistory] = useState<ArenaMatch[]>([]);

  useEffect(() => {
    modelsApi.list().then(setModels).catch(() => {});
    arenaApi.list().then(setHistory).catch(() => {});
  }, []);

  const modelMap = Object.fromEntries(models.map(m => [m.id, m.name]));

  const startBattle = async () => {
    if (!modelA || !modelB || !prompt.trim()) {
      message.warning("请选择两个模型并输入提示词");
      return;
    }
    setLoading(true);
    setMatch(null);
    try {
      const m = await arenaApi.createMatch({ prompt, model_a_id: modelA, model_b_id: modelB });
      setMatch(m);
    } catch {
      message.error("对战失败");
    } finally {
      setLoading(false);
    }
  };

  const handleVote = async (winner: string) => {
    if (!match) return;
    setVoting(true);
    try {
      const updated = await arenaApi.vote(match.id, winner);
      setMatch(updated);
      message.success("投票成功！ELO分数已更新");
      arenaApi.list().then(setHistory).catch(() => {});
    } catch {
      message.error("投票失败");
    } finally {
      setVoting(false);
    }
  };

  return (
    <div className="page-fade-in">
      <Title level={2}>模型竞技场</Title>
      <Text type="secondary">盲测对比两个模型的输出，投票决定胜负，自动更新ELO排名</Text>

      <Card style={{ marginTop: 16 }}>
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Select style={{ width: "100%" }} placeholder="选择模型 A" value={modelA} onChange={setModelA}
              options={models.map(m => ({ value: m.id, label: `${m.name} (${m.model_name})` }))} />
          </Col>
          <Col xs={24} sm={12}>
            <Select style={{ width: "100%" }} placeholder="选择模型 B" value={modelB} onChange={setModelB}
              options={models.map(m => ({ value: m.id, label: `${m.name} (${m.model_name})` }))} />
          </Col>
        </Row>
        <TextArea rows={3} placeholder="输入提示词..." value={prompt} onChange={(e) => setPrompt(e.target.value)} style={{ marginTop: 12 }} />
        <Button type="primary" icon={<ThunderboltOutlined />} onClick={startBattle} loading={loading} style={{ marginTop: 12 }}>
          开始对战
        </Button>
      </Card>

      {loading && <div style={{ textAlign: "center", margin: 24 }}><Spin size="large" tip="模型正在思考中..." /></div>}

      {match && !loading && (
        <>
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title={match.winner ? `模型 A: ${modelMap[match.model_a_id] || ""}` : "模型 A (盲测)"}
                extra={match.latency_a_ms ? <Tag>{Math.round(match.latency_a_ms)}ms</Tag> : null}
                style={{ borderTop: match.winner === "a" ? "3px solid #52c41a" : match.winner === "b" ? "3px solid #ff4d4f" : undefined }}>
                <Paragraph style={{ whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" }}>{match.output_a}</Paragraph>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title={match.winner ? `模型 B: ${modelMap[match.model_b_id] || ""}` : "模型 B (盲测)"}
                extra={match.latency_b_ms ? <Tag>{Math.round(match.latency_b_ms)}ms</Tag> : null}
                style={{ borderTop: match.winner === "b" ? "3px solid #52c41a" : match.winner === "a" ? "3px solid #ff4d4f" : undefined }}>
                <Paragraph style={{ whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" }}>{match.output_b}</Paragraph>
              </Card>
            </Col>
          </Row>

          {!match.winner && (
            <Card style={{ marginTop: 16, textAlign: "center" }}>
              <Text strong style={{ fontSize: 16 }}>哪个模型的回答更好？</Text>
              <div style={{ marginTop: 12 }}>
                <Space size="large">
                  <Button size="large" type="primary" ghost onClick={() => handleVote("a")} loading={voting}>A 更好</Button>
                  <Button size="large" onClick={() => handleVote("tie")} loading={voting}>平局</Button>
                  <Button size="large" type="primary" ghost onClick={() => handleVote("b")} loading={voting}>B 更好</Button>
                </Space>
              </div>
            </Card>
          )}
          {match.winner && (
            <Card style={{ marginTop: 16, textAlign: "center" }}>
              <Tag color={match.winner === "tie" ? "default" : "success"} style={{ fontSize: 16, padding: "4px 16px" }}>
                {match.winner === "a" ? `胜者: ${modelMap[match.model_a_id]}` : match.winner === "b" ? `胜者: ${modelMap[match.model_b_id]}` : "平局"}
              </Tag>
            </Card>
          )}
        </>
      )}

      <Divider />
      <Card title="对战历史">
        <Table
          dataSource={history}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          columns={[
            { title: "提示词", dataIndex: "prompt", key: "prompt", ellipsis: true },
            { title: "模型A", dataIndex: "model_a_id", key: "a", render: (id: number) => modelMap[id] || `#${id}` },
            { title: "模型B", dataIndex: "model_b_id", key: "b", render: (id: number) => modelMap[id] || `#${id}` },
            { title: "胜者", dataIndex: "winner", key: "winner", render: (w: string, r: ArenaMatch) =>
              w === "a" ? <Tag color="blue">{modelMap[r.model_a_id]}</Tag> : w === "b" ? <Tag color="green">{modelMap[r.model_b_id]}</Tag> : w === "tie" ? <Tag>平局</Tag> : <Tag color="default">未投票</Tag>
            },
          ]}
        />
      </Card>
    </div>
  );
}
