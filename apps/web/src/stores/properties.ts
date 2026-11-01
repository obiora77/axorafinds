import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiFetch, parseApiError } from '@/lib/api'
import type { Paged, PropertyCardData, PropertyDetailData, PropertyFilters } from '@/types'

function toQuery(filters: PropertyFilters, page: number, pageSize?: number): Record<string, string | number> {
  const query: Record<string, string | number> = { page }
  for (const [key, value] of Object.entries(filters)) {
    if (value) query[key] = value
  }
  if (pageSize) query.page_size = pageSize
  return query
}

export const usePropertiesStore = defineStore('properties', () => {
  // The browse grid
  const items = ref<PropertyCardData[]>([])
  const count = ref(0)
  const page = ref(1)
  const hasMore = ref(false)
  const loading = ref(false)
  const error = ref('')
  let sequence = 0

  // The "latest listings" strip on the home page
  const latest = ref<PropertyCardData[]>([])
  const latestLoading = ref(false)
  const latestError = ref('')
  const total = ref(0)

  // An owner's own listings, at every stage of review
  const mine = ref<PropertyDetailData[]>([])
  const mineLoading = ref(false)
  const mineError = ref('')

  async function fetchList(filters: PropertyFilters = {}, append = false): Promise<void> {
    const mine = ++sequence
    const nextPage = append ? page.value + 1 : 1
    loading.value = true
    error.value = ''
    try {
      const data = await apiFetch<Paged<PropertyCardData>>('/properties', { query: toQuery(filters, nextPage) })
      if (mine !== sequence) return // a newer request replaced this one
      items.value = append ? [...items.value, ...data.results] : data.results
      count.value = data.count
      page.value = nextPage
      hasMore.value = data.next !== null
    } catch (e) {
      if (mine !== sequence) return
      error.value = parseApiError(e).message
      if (!append) {
        items.value = []
        count.value = 0
        hasMore.value = false
      }
    } finally {
      if (mine === sequence) loading.value = false
    }
  }

  function loadMore(filters: PropertyFilters = {}): Promise<void> {
    return fetchList(filters, true)
  }

  async function fetchLatest(size = 8): Promise<void> {
    latestLoading.value = true
    latestError.value = ''
    try {
      const data = await apiFetch<Paged<PropertyCardData>>('/properties', { query: { page: 1, page_size: size } })
      latest.value = data.results
      total.value = data.count
    } catch (e) {
      latestError.value = parseApiError(e).message
    } finally {
      latestLoading.value = false
    }
  }

  async function fetchMine(): Promise<void> {
    mineLoading.value = true
    mineError.value = ''
    mine.value = []
    try {
      mine.value = await apiFetch<PropertyDetailData[]>('/properties/mine')
    } catch (e) {
      mineError.value = parseApiError(e).message
    } finally {
      mineLoading.value = false
    }
  }

  function fetchOne(slug: string): Promise<PropertyDetailData> {
    return apiFetch<PropertyDetailData>(`/properties/${encodeURIComponent(slug)}`)
  }

  /** Owner listing submission. Always comes back pending until staff publish it. */
  function create(form: FormData): Promise<PropertyDetailData> {
    return apiFetch<PropertyDetailData>('/properties', { method: 'POST', body: form })
  }

  return {
    items, count, hasMore, loading, error,
    latest, latestLoading, latestError, total,
    mine, mineLoading, mineError,
    fetchList, loadMore, fetchLatest, fetchMine, fetchOne, create,
  }
})
