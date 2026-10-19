import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiFetch } from '@/lib/api'
import type { PropertyCardData } from '@/types'

export const useFavoritesStore = defineStore('favorites', () => {
  const ids = ref<Set<number>>(new Set())

  function has(id: number): boolean {
    return ids.value.has(id)
  }

  function setLocal(id: number, on: boolean): void {
    const next = new Set(ids.value)
    if (on) next.add(id)
    else next.delete(id)
    ids.value = next
  }

  /** Loads the signed-in seeker's saved properties so hearts persist across sessions. */
  async function load(): Promise<void> {
    try {
      const saved = await apiFetch<PropertyCardData[]>('/favorites')
      ids.value = new Set(saved.map((p) => p.id))
    } catch {
      ids.value = new Set()
    }
  }

  function reset(): void {
    ids.value = new Set()
  }

  /** Optimistic toggle; rolls back and rethrows if the server refuses. */
  async function toggle(id: number): Promise<void> {
    const wasFavorite = ids.value.has(id)
    setLocal(id, !wasFavorite)
    try {
      await apiFetch(`/favorites/${id}`, { method: wasFavorite ? 'DELETE' : 'POST' })
    } catch (error) {
      setLocal(id, wasFavorite)
      throw error
    }
  }

  return { ids, has, load, reset, toggle }
})
