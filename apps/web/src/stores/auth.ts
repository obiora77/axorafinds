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

  return { user, ready, isAuthed, role, isOwner, isSeeker, restore, login, register, logout }
})
