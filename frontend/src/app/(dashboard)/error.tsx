"use client";

import { Button, Result } from "antd";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <Result
      status="error"
      title="页面出现错误"
      subTitle={error.message || "抱歉，页面加载时遇到了问题。请尝试刷新页面。"}
      extra={[
        <Button type="primary" key="retry" onClick={reset}>
          重试
        </Button>,
        <Button key="home" href="/dashboard">
          返回首页
        </Button>,
      ]}
    />
  );
}
