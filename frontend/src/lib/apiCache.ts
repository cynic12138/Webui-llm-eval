/**
 * Simple in-memory cache for API responses.
 * Caches GET requests with a configurable TTL to avoid redundant requests
 * when navigating between pages.
 */

interface CacheEntry<T> {
  data: T;
  expireAt: number;
}

const MAX_CACHE_SIZE = 100;
const cache = new Map<string, CacheEntry<unknown>>();
const pendingRequests = new Map<string, Promise<unknown>>();

const DEFAULT_TTL = 30_000; // 30 seconds

function evictExpired(): void {
  const now = Date.now();
  const keys = Array.from(cache.keys());
  for (const key of keys) {
    const entry = cache.get(key);
    if (entry && now > entry.expireAt) {
      cache.delete(key);
    }
  }
}

export function getCached<T>(key: string): T | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() > entry.expireAt) {
    cache.delete(key);
    return null;
  }
  return entry.data as T;
}

export function setCache<T>(key: string, data: T, ttl = DEFAULT_TTL): void {
  // Evict if cache is too large
  if (cache.size >= MAX_CACHE_SIZE) {
    evictExpired();
    // If still too large, delete oldest entries
    if (cache.size >= MAX_CACHE_SIZE) {
      const firstKey = cache.keys().next().value;
      if (firstKey) cache.delete(firstKey);
    }
  }
  cache.set(key, { data, expireAt: Date.now() + ttl });
}

export function invalidateCache(prefix?: string): void {
  if (!prefix) {
    cache.clear();
    emitDataChange("all");
    return;
  }
  const keys = Array.from(cache.keys());
  for (const key of keys) {
    if (key.startsWith(prefix)) {
      cache.delete(key);
    }
  }
  // Notify subscribers that data has changed
  emitDataChange(prefix.replace(/:$/, ""));
}

// ─── Lightweight data-change event bus ───
// Pages subscribe via onDataChange() and re-fetch when relevant data mutates.
type DataChangeListener = (scope: string) => void;
const listeners = new Set<DataChangeListener>();

function emitDataChange(scope: string): void {
  listeners.forEach((fn) => fn(scope));
}

/** Subscribe to data-change events. Returns an unsubscribe function. */
export function onDataChange(callback: DataChangeListener): () => void {
  listeners.add(callback);
  return () => { listeners.delete(callback); };
}

/**
 * Wraps an async fetch function with caching and request deduplication.
 * Returns cached data if available, otherwise calls the fetcher.
 * Concurrent requests for the same key are deduplicated.
 */
export async function cachedFetch<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl = DEFAULT_TTL,
): Promise<T> {
  const cached = getCached<T>(key);
  if (cached !== null) return cached;

  // Deduplicate concurrent requests for the same key
  const pending = pendingRequests.get(key);
  if (pending) return pending as Promise<T>;

  const promise = fetcher()
    .then((data) => {
      setCache(key, data, ttl);
      return data;
    })
    .finally(() => {
      pendingRequests.delete(key);
    });

  pendingRequests.set(key, promise);
  return promise;
}
