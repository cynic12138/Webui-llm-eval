"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Layout, Menu, Avatar, Dropdown, Button, Typography, Badge } from "antd";
import {
  DashboardOutlined, RobotOutlined, DatabaseOutlined,
  ExperimentOutlined, TrophyOutlined,
  BookOutlined, SettingOutlined, UserOutlined, LogoutOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined, BellOutlined,
  FileTextOutlined, SwapOutlined, ThunderboltOutlined, KeyOutlined, TeamOutlined,
  SafetyCertificateOutlined, QuestionCircleOutlined,
} from "@ant-design/icons";
import { SunOutlined, MoonOutlined } from "@ant-design/icons";
import { isAuthenticated, getUser, clearAuth } from "@/lib/auth";
import { useTheme } from "@/app/providers";
import type { User } from "@/types";
import Link from "next/link";
import FloatingAssistant from "@/components/agent/FloatingAssistant";
import NotificationCenter from "@/components/NotificationCenter";

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: "/dashboard", icon: <DashboardOutlined />, label: <Link href="/dashboard">概览</Link> },
  { key: "/models", icon: <RobotOutlined />, label: <Link href="/models">模型管理</Link> },
  { key: "/datasets", icon: <DatabaseOutlined />, label: <Link href="/datasets">数据集</Link> },
  {
    key: "evaluations",
    icon: <ExperimentOutlined />,
    label: "评测任务",
    children: [
      { key: "/evaluations", label: <Link href="/evaluations">任务列表</Link> },
      { key: "/evaluations/new", label: <Link href="/evaluations/new">创建评测</Link> },
    ],
  },
  { key: "/comparison", icon: <SwapOutlined />, label: <Link href="/comparison">对比分析</Link> },
  { key: "/prompts", icon: <FileTextOutlined />, label: <Link href="/prompts">提示词工程</Link> },
  { key: "/leaderboard", icon: <TrophyOutlined />, label: <Link href="/leaderboard">ELO排行榜</Link> },
  { key: "/arena", icon: <ThunderboltOutlined />, label: <Link href="/arena">模型竞技场</Link> },
  { key: "/benchmarks", icon: <BookOutlined />, label: <Link href="/benchmarks">标准基准</Link> },
  { key: "/teams", icon: <TeamOutlined />, label: <Link href="/teams">团队协作</Link> },
  { key: "/settings/judge-models", icon: <SafetyCertificateOutlined />, label: <Link href="/settings/judge-models">裁判模型</Link> },
  { key: "/settings/agent-model", icon: <RobotOutlined />, label: <Link href="/settings/agent-model">AI助手模型</Link> },
  { key: "/settings/api-keys", icon: <KeyOutlined />, label: <Link href="/settings/api-keys">API 密钥</Link> },
  { key: "/admin", icon: <SettingOutlined />, label: <Link href="/admin">系统管理</Link> },
  { type: "divider" as const, key: "divider" },
  { key: "/guide", icon: <QuestionCircleOutlined />, label: <Link href="/guide">功能指南</Link> },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const { isDark, toggle: toggleTheme } = useTheme();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    setUser(getUser());
  }, [router]);

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  const selectedKeys = useMemo(() => [pathname], [pathname]);
  const openKeys = useMemo(
    () => pathname.startsWith("/evaluations") ? ["evaluations"] : [],
    [pathname]
  );

  const userMenuItems = [
    { key: "profile", icon: <UserOutlined />, label: "个人信息", onClick: () => router.push("/settings/profile") },
    { key: "divider", type: "divider" as const },
    { key: "logout", icon: <LogoutOutlined />, label: "退出登录", danger: true, onClick: handleLogout },
  ];

  const siderWidth = collapsed ? 80 : 240;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        theme="dark"
        width={240}
        style={{ overflow: "auto", height: "100vh", position: "fixed", left: 0, top: 0, bottom: 0 }}
      >
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">
            <ExperimentOutlined />
          </div>
          {!collapsed && <span className="sidebar-brand-text">LLM 评测平台</span>}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={selectedKeys}
          defaultOpenKeys={openKeys}
          items={menuItems}
        />
      </Sider>

      <Layout style={{ marginLeft: siderWidth, transition: "margin-left 0.2s cubic-bezier(0.4, 0, 0.2, 1)" }}>
        <Header className="app-header">
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            className="header-toggle-btn"
          />
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Button
              type="text"
              className="header-toggle-btn"
              icon={isDark ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
              title={isDark ? "切换亮色模式" : "切换暗色模式"}
            />
            <NotificationCenter />
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <div className="header-user-area">
                <Avatar
                  size={32}
                  style={{ background: "linear-gradient(135deg, #4f6ef7, #7c5cf7)" }}
                  icon={<UserOutlined />}
                />
                {!collapsed && (
                  <span className="header-user-name">{user?.full_name || user?.username}</span>
                )}
              </div>
            </Dropdown>
          </div>
        </Header>

        <Content style={{ margin: 24, minHeight: "calc(100vh - 88px)" }}>
          {children}
        </Content>
      </Layout>

      <FloatingAssistant />
    </Layout>
  );
}
