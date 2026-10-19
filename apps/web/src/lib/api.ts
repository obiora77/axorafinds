import { ofetch, FetchError, type FetchOptions } from 'ofetch'

const BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')
const ACCESS_KEY = 'axora.access'
const REFRESH_KEY = 'axora.refresh'

export const AUTH_LOST_EVENT = 'axora:auth-lost'

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    /* storage unavailable (private mode); the session just won't persist */
  }
}

export const tokenStore = {
  get access(): string | null {
    return read(ACCESS_KEY)
  },
  get refresh(): string | null {
    return read(REFRESH_KEY)
  },
  set(access: string, refresh?: string): void {
    write(ACCESS_KEY, access)
    if (refresh) write(REFRESH_KEY, refresh)
  },
  clear(): void {
    write(ACCESS_KEY, null)
    write(REFRESH_KEY, null)
  },
}

const client = ofetch.create({ baseURL: BASE })

type ApiOptions = FetchOptions<'json'> & {
  /** Set false to skip the Authorization header (login, register). */
  auth?: boolean
}

let refreshing: Promise<boolean> | null = null

function refreshAccess(): Promise<boolean> {
  const refresh = tokenStore.refresh
  if (!refresh) return Promise.resolve(false)
  refreshing ??= client<{ access: string; refresh?: string }>('/auth/token/refresh', {
    method: 'POST',
    body: { refresh },
  })
    .then((r) => {
      tokenStore.set(r.access, r.refresh)
      return true
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

function withAuth(options: ApiOptions): FetchOptions<'json'> {
  const { auth = true, ...rest } = options
  const token = auth ? tokenStore.access : null
  if (!token) return rest
  const headers = new Headers(rest.headers)
  headers.set('Authorization', `Bearer ${token}`)
  return { ...rest, headers }
}

/**
 * JSON request against the Django API. Adds the access token when there is one,
 * refreshes it once on a 401, and if the session is truly gone clears it and retries
 * anonymously so public endpoints (like requesting an inspection) never fail on a stale token.
 */
export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  try {
    return await client<T>(path, withAuth(options))
  } catch (error) {
    const hadToken = options.auth !== false && Boolean(tokenStore.access)
    if (error instanceof FetchError && error.status === 401 && hadToken) {
      if (await refreshAccess()) {
        try {
          return await client<T>(path, withAuth(options))
        } catch (retryError) {
          if (!(retryError instanceof FetchError && retryError.status === 401)) throw retryError
        }
      }
      tokenStore.clear()
      window.dispatchEvent(new Event(AUTH_LOST_EVENT))
      return await client<T>(path, withAuth({ ...options, auth: false }))
    }
    throw error
  }
}

export interface ParsedApiError {
  message: string
  fields: Record<string, string>
}

/** Turns a DRF error body into one message plus per-field messages. */
export function parseApiError(error: unknown): ParsedApiError {
  const fallback = 'Something went wrong. Please try again.'

  if (!(error instanceof FetchError)) return { message: fallback, fields: {} }
  if (!error.response) {
    return { message: 'Could not reach the server. Check your connection and try again.', fields: {} }
  }
  if (error.status === 429) {
    return { message: 'Too many attempts. Please wait a while and try again.', fields: {} }
  }

  const data: unknown = error.data
  if (data && typeof data === 'object') {
    const fields: Record<string, string> = {}
    let message = ''
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      const text = Array.isArray(value) ? value.map(String).join(' ') : typeof value === 'string' ? value : ''
      if (!text) continue
      if (key === 'detail' || key === 'non_field_errors') message = text
      else fields[key] = text
    }
    if (!message && Object.keys(fields).length) message = 'Please check the highlighted fields.'
    return { message: message || fallback, fields }
  }
  return { message: fallback, fields: {} }
}
