"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider, theme } from "antd";
import { StyleProvider } from "@ant-design/cssinjs";

interface ThemeContextType {
  isDark: boolean;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextType>({ isDark: false, toggle: () => {} });
export const useTheme = () => useContext(ThemeContext);

export default function Providers({ children }: { children: React.ReactNode }) {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || saved === "light") {
      const dark = saved === "dark";
      setIsDark(dark);
      document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    } else {
      // Auto-detect system preference when user hasn't explicitly chosen
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setIsDark(prefersDark);
      document.documentElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
    }

    // Listen for system theme changes (only when user hasn't set explicit preference)
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem("theme")) {
        setIsDark(e.matches);
        document.documentElement.setAttribute("data-theme", e.matches ? "dark" : "light");
      }
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const toggle = useCallback(() => {
    setIsDark((prev) => {
      const next = !prev;
      localStorage.setItem("theme", next ? "dark" : "light");
      document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ isDark, toggle }}>
      <AntdRegistry>
        <StyleProvider hashPriority="high">
          <ConfigProvider
            theme={{
              algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
              token: {
                colorPrimary: "#4f6ef7",
                colorInfo: "#4f6ef7",
                colorSuccess: "#10b981",
                colorWarning: "#f59e0b",
                colorError: "#ef4444",
                borderRadius: 10,
                fontFamily:
                  "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif",
                controlHeight: 36,
                fontSize: 14,
                colorBgLayout: isDark ? "#0f1117" : "#f4f6fb",
                colorBorderSecondary: isDark ? "#23262f" : "#f0f2f8",
              },
              components: {
                Button: {
                  controlHeight: 36,
                  primaryShadow: "0 4px 12px rgba(79, 110, 247, 0.25)",
                  borderRadius: 8,
                },
                Card: {
                  borderRadiusLG: 14,
                  paddingLG: 24,
                },
                Table: {
                  headerBg: isDark ? "#1a1d29" : "#f8f9fc",
                  headerColor: isDark ? "#9aa0a6" : "#6b7280",
                  headerSplitColor: "transparent",
                  borderColor: isDark ? "#2d3039" : "#f0f2f8",
                  rowHoverBg: isDark ? "#252836" : "#f8f9fe",
                },
                Input: {
                  borderRadius: 8,
                  controlHeight: 40,
                },
                Select: {
                  borderRadius: 8,
                  controlHeight: 40,
                },
                Menu: {
                  darkItemBg: "transparent",
                  darkSubMenuItemBg: "transparent",
                  darkItemSelectedBg: "rgba(79, 110, 247, 0.2)",
                  darkItemHoverBg: "rgba(255, 255, 255, 0.06)",
                  darkItemSelectedColor: "#ffffff",
                  itemBorderRadius: 6,
                  darkItemColor: "rgba(255, 255, 255, 0.6)",
                },
                Tag: {
                  borderRadiusSM: 6,
                },
                Modal: {
                  borderRadiusLG: 14,
                },
                Statistic: {
                  contentFontSize: 28,
                },
              },
            }}
          >
            {children}
          </ConfigProvider>
        </StyleProvider>
      </AntdRegistry>
    </ThemeContext.Provider>
  );
}
