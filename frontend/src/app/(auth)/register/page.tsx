"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Form, Input, Button, Alert } from "antd";
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  ArrowLeftOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
} from "@ant-design/icons";
import { authApi } from "@/lib/api";
import Link from "next/link";

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onFinish = async (values: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
  }) => {
    setLoading(true);
    setError("");
    try {
      await authApi.register(values);
      router.push("/login?registered=1");
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError?.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-brand">
        <div className="auth-decor-diamond" />
        <div className="auth-decor-triangle" />
        <div className="auth-brand-content">
          <div className="auth-brand-logo">LLM 评测平台</div>
          <div className="auth-brand-slogan">
            企业级大模型评测系统，助您精准选择最佳 AI 模型
          </div>
          <div className="auth-features">
            <div className="auth-feature">
              <div className="auth-feature-icon">
                <ExperimentOutlined />
              </div>
              <div className="auth-feature-text">
                <h4>多维度评测</h4>
                <p>支持准确性、流畅性、安全性等多指标全方位评估</p>
              </div>
            </div>
            <div className="auth-feature">
              <div className="auth-feature-icon">
                <ThunderboltOutlined />
              </div>
              <div className="auth-feature-text">
                <h4>自动化流程</h4>
                <p>一键启动批量评测，自动生成专业评测报告</p>
              </div>
            </div>
            <div className="auth-feature">
              <div className="auth-feature-icon">
                <BarChartOutlined />
              </div>
              <div className="auth-feature-text">
                <h4>ELO 排行榜</h4>
                <p>基于 ELO 算法的公正排名，直观对比模型能力</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="auth-form-side">
        <div className="auth-form-wrapper">
          <Link href="/login" className="auth-back-btn">
            <ArrowLeftOutlined /> 返回登录
          </Link>
          <div className="auth-form-title">创建账号</div>
          <span className="auth-form-subtitle">
            注册加入 LLM 评测平台
          </span>

          {error && (
            <Alert message={error} type="error" showIcon className="auth-alert" />
          )}

          <Form onFinish={onFinish} layout="vertical" size="large">
            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true }]}
            >
              <Input prefix={<UserOutlined />} placeholder="请输入用户名" />
            </Form.Item>
            <Form.Item name="full_name" label="姓名">
              <Input
                prefix={<UserOutlined />}
                placeholder="请输入真实姓名（可选）"
              />
            </Form.Item>
            <Form.Item
              name="email"
              label="邮箱"
              rules={[{ required: true, type: "email" }]}
            >
              <Input prefix={<MailOutlined />} placeholder="请输入邮箱" />
            </Form.Item>
            <Form.Item
              name="password"
              label="密码"
              rules={[{ required: true, min: 6 }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="至少6位密码"
              />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                block
                loading={loading}
                className="auth-submit-btn"
              >
                注册
              </Button>
            </Form.Item>
          </Form>

          <div className="auth-footer-link">
            已有账号？ <Link href="/login">立即登录</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
