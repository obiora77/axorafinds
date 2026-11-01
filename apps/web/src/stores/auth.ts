import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { apiFetch, tokenStore, AUTH_LOST_EVENT } from '@/lib/api'
import { useFavoritesStore } from '@/stores/favorites'
import type { AuthResponse, Role, User } from '@/types'

export interface RegisterPayload {
  name: string
  email: string
  password: string
  phone?: string
  role: 'seeker' | 'owner'
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const ready = ref(false)

  const isAuthed = computed(() => user.value !== null)
  const role = computed<Role | null>(() => user.value?.role ?? null)
  const isOwner = computed(() => role.value === 'owner')
  const isSeeker = computed(() => role.value === 'seeker')
  // The API gate is `is_staff`, so mirror it here: any Django staff account or
  // superuser reaches the dashboard, even if its role is not "staff".
  const isStaff = computed(() => user.value?.is_staff === true || role.value === 'staff')

  function startSession(response: AuthResponse): void {
    tokenStore.set(response.access, response.refresh)
    user.value = response.user
    if (response.user.role === 'seeker') void useFavoritesStore().load()
  }

  /** Restores the session from stored tokens on first load. */
  async function restore(): Promise<void> {
    if (ready.value) return
    if (tokenStore.access || tokenStore.refresh) {
      try {
        user.value = await apiFetch<User>('/auth/me')
        if (user.value.role === 'seeker') void useFavoritesStore().load()
      } catch {
        tokenStore.clear()
        user.value = null
      }
    }
    ready.value = true
  }

  async function login(email: string, password: string): Promise<void> {
    startSession(
      await apiFetch<AuthResponse>('/auth/token', { method: 'POST', body: { email, password }, auth: false }),
    )
  }

  async function register(payload: RegisterPayload): Promise<void> {
    startSession(await apiFetch<AuthResponse>('/auth/register', { method: 'POST', body: payload, auth: false }))
  }

  async function verifyOtp(email: string, code: string, purpose: 'signup' | 'password_reset' = 'signup'): Promise<void> {
    const result = await apiFetch<AuthResponse & { detail: string}>('/auth/verify-otp', { method: 'POST', body: { email, code, purpose }, auth: false })
    if (purpose === 'signup') startSession(result)  
  }

  async function resendOtp(email: string, purpose: 'signup' | 'password_reset' = 'signup'): Promise<void> {
    await apiFetch('/auth/resend-otp', { method: 'POST', body: { email, purpose }, auth: false })
  }

  async function requestPasswordReset(email: string): Promise<void> {
    await apiFetch('/auth/password-reset/request', { method: 'POST', body: { email }, auth: false })
  }

  async function confirmPasswordReset(email: string, code: string, password: string): Promise<void> {
    await apiFetch('/auth/password-reset/confirm', { method: 'POST', body: { email, code, password }, auth: false })
  }

  function logout(): void {
    tokenStore.clear()
    user.value = null
    useFavoritesStore().reset()
  }

  // If a refresh fails mid-session, the API layer clears the tokens and tells us.
  window.addEventListener(AUTH_LOST_EVENT, () => {
    user.value = null
    useFavoritesStore().reset()
  })

  return { user, ready, isAuthed, role, isOwner, isSeeker, isStaff, restore, login, register, verifyOtp, resendOtp, requestPasswordReset, confirmPasswordReset, logout }
})
