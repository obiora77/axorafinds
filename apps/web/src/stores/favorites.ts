import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiFetch } from '@/lib/api'
import type { PropertyCardData } from '@/types'

export const useFavoritesStore = defineStore('favorites', () => {
  const ids = ref<Set<number>>(new Set())
  const saved = ref<PropertyCardData[]>([])
  const savedLoading = ref(false)

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
    savedLoading.value = true
    try {
      const items = await apiFetch<PropertyCardData[]>('/favorites')
      ids.value = new Set(items.map((p) => p.id))
      saved.value = items
    } catch {
      ids.value = new Set()
      saved.value = []
    } finally {
      savedLoading.value = false
    }
  }

  function reset(): void {
    ids.value = new Set()
    saved.value = []
  }

  /** Optimistic toggle; rolls back the heart and the saved list if the server refuses. */
  async function toggle(property: PropertyCardData): Promise<void> {
    const id = property.id
    const wasFavorite = ids.value.has(id)
    const previousSaved = saved.value
    setLocal(id, !wasFavorite)
    saved.value = wasFavorite ? saved.value.filter((p) => p.id !== id) : [property, ...saved.value]
    try {
      await apiFetch(`/favorites/${id}`, { method: wasFavorite ? 'DELETE' : 'POST' })
    } catch (error) {
      setLocal(id, wasFavorite)
      saved.value = previousSaved
      throw error
    }
  }

  return { ids, saved, savedLoading, has, load, reset, toggle }
})
