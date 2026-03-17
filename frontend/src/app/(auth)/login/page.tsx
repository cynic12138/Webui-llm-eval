"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Form, Input, Button, Alert } from "antd";
import {
  UserOutlined,
  LockOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
} from "@ant-design/icons";
import { authApi } from "@/lib/api";
import { saveAuth } from "@/lib/auth";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    setError("");
    try {
      const token = await authApi.login(values.username, values.password);
      saveAuth(token);
      router.push("/dashboard");
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError?.response?.data?.detail || "Login failed");
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
          <div className="auth-form-title">欢迎回来</div>
          <span className="auth-form-subtitle">登录您的账号以继续使用平台</span>

          {error && (
            <Alert message={error} type="error" showIcon className="auth-alert" />
          )}

          <Form onFinish={onFinish} layout="vertical" size="large">
            <Form.Item
              name="username"
              rules={[{ required: true, message: "请输入用户名" }]}
            >
              <Input prefix={<UserOutlined />} placeholder="用户名" />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[{ required: true, message: "请输入密码" }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                block
                loading={loading}
                className="auth-submit-btn"
              >
                登录
              </Button>
            </Form.Item>
          </Form>

          <div className="auth-footer-link">
            还没有账号？ <Link href="/register">立即注册</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
