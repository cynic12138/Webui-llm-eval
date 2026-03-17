"use client";

import { Button, Result } from "antd";

export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
      <Result
        status="error"
        title="页面出现错误"
        subTitle={error.message || "抱歉，页面加载时遇到了问题。"}
        extra={[
          <Button type="primary" key="retry" onClick={reset}>
            重试
          </Button>,
          <Button key="login" href="/login">
            返回登录
          </Button>,
        ]}
      />
    </div>
  );
}
