/**
 * Hook: auto-refresh data when a relevant mutation happens anywhere in the app.
 *
 * Usage:
 *   useDataRefresh(["evaluations", "models"], loadData);
 *
 * When any API mutation calls invalidateCache("evaluations:..."),
 * `loadData` will be invoked automatically so the page refreshes.
 */
import { useEffect, useRef } from "react";
import { onDataChange } from "./apiCache";

export function useDataRefresh(
  /** Cache-key scopes to listen for, e.g. ["evaluations", "models"] */
  scopes: string[],
  /** Callback to re-fetch data */
  refresh: () => void,
): void {
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  useEffect(() => {
    const unsub = onDataChange((scope) => {
      if (scope === "all" || scopes.includes(scope)) {
        refreshRef.current();
      }
    });
    return unsub;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scopes.join(",")]);
}
