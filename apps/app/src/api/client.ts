/**
 * HTTP client.
 *
 * Owns three things the rest of the app should never think about: where the API
 * lives, attaching the bearer token, and transparently refreshing that token
 * when it expires mid-session.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

import type { TokenPair } from './types';

const TOKEN_KEY = 'pramonit.tokens.v1';

export function resolveBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_API_URL;
  if (configured) return configured.replace(/\/$/, '');

  // On web in development the API is a sibling process on the same host, which
  // keeps the setup to two terminals and no tunnelling.
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:8000/api`;
  }
  return 'http://localhost:8000/api';
}

export const BASE_URL = resolveBaseUrl();

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/** FastAPI returns 422 details as an array of per-field objects. */
function readDetail(payload: any, fallback: string): string {
  const detail = payload?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item: any) => {
        const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : null;
        return field ? `${String(field).replace(/_/g, ' ')}: ${item.msg}` : item.msg;
      })
      .join('\n');
  }
  return fallback;
}

// ---------------------------------------------------------------- token store

let cachedTokens: TokenPair | null = null;

export async function loadTokens(): Promise<TokenPair | null> {
  if (cachedTokens) return cachedTokens;
  try {
    const raw = await AsyncStorage.getItem(TOKEN_KEY);
    cachedTokens = raw ? (JSON.parse(raw) as TokenPair) : null;
  } catch {
    cachedTokens = null;
  }
  return cachedTokens;
}

export async function saveTokens(tokens: TokenPair | null): Promise<void> {
  cachedTokens = tokens;
  try {
    if (tokens) await AsyncStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
    else await AsyncStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable — the session simply will not survive a reload */
  }
}

// ------------------------------------------------------------------- requests

type Options = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  auth?: boolean;
  signal?: AbortSignal;
};

let refreshInFlight: Promise<TokenPair | null> | null = null;

async function refreshTokens(): Promise<TokenPair | null> {
  const tokens = await loadTokens();
  if (!tokens?.refresh_token) return null;

  // A single in-flight refresh, shared by every request that hit 401 at once —
  // otherwise a screen with four queries fires four refreshes and three of them
  // race to overwrite the result.
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const response = await fetch(`${BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: tokens.refresh_token }),
        });
        if (!response.ok) {
          await saveTokens(null);
          return null;
        }
        const fresh = (await response.json()) as TokenPair;
        await saveTokens(fresh);
        return fresh;
      } catch {
        return null;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

export async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { method = 'GET', body, auth = true, signal } = options;

  const send = async (token?: string): Promise<Response> => {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (token) headers.Authorization = `Bearer ${token}`;

    return fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  };

  let tokens = auth ? await loadTokens() : null;
  let response: Response;

  try {
    response = await send(tokens?.access_token);
  } catch (error: any) {
    if (error?.name === 'AbortError') throw error;
    throw new ApiError(
      0,
      null,
      `Cannot reach the Pramonit API at ${BASE_URL}. Is the backend running?`,
    );
  }

  if (response.status === 401 && auth && tokens?.refresh_token) {
    const fresh = await refreshTokens();
    if (fresh) {
      tokens = fresh;
      response = await send(fresh.access_token);
    }
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const payload = text ? safeParse(text) : null;

  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload?.detail ?? null,
      readDetail(payload, `Request failed (${response.status})`),
    );
  }

  return payload as T;
}

function safeParse(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export const api = {
  get: <T,>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T,>(path: string, body?: unknown, auth = true) =>
    request<T>(path, { method: 'POST', body, auth }),
  patch: <T,>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
};
