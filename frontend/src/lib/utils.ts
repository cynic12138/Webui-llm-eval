import dayjs from "dayjs";

export function formatDate(date: string | undefined): string {
  if (!date) return "-";
  return dayjs(date).format("YYYY-MM-DD HH:mm");
}

export function formatDuration(startAt: string | undefined, endAt: string | undefined): string {
  if (!startAt) return "-";
  const end = endAt ? dayjs(endAt) : dayjs();
  const diff = end.diff(dayjs(startAt), "second");
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s`;
  return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`;
}

export function formatScore(score: number): string {
  return (score * 100).toFixed(1) + "%";
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: "default",
    running: "processing",
    completed: "success",
    failed: "error",
    cancelled: "warning",
  };
  return colors[status] || "default";
}

export function truncate(text: string, length = 100): string {
  if (!text) return "";
  return text.length > length ? text.slice(0, length) + "..." : text;
}
