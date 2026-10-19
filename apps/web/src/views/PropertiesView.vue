<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FilterBar from '@/components/FilterBar.vue'
import PropertyCard from '@/components/PropertyCard.vue'
import { gridStagger } from '@/plugins/motion'
import { usePropertiesStore } from '@/stores/properties'
import type { PropertyFilters } from '@/types'

const route = useRoute()
const router = useRouter()
const store = usePropertiesStore()

const FILTER_KEYS = ['q', 'state', 'city', 'type', 'max_price', 'bedrooms'] as const

const filters = computed<PropertyFilters>(() => {
  const result: PropertyFilters = {}
  for (const key of FILTER_KEYS) {
    const raw = route.query[key]
    const value = Array.isArray(raw) ? raw[0] : raw
    if (typeof value === 'string' && value) result[key] = value
  }
  return result
})

function applyFilters(next: PropertyFilters): void {
  const query: Record<string, string> = {}
  for (const key of FILTER_KEYS) {
    const value = String(next[key] ?? '').trim()
    if (value) query[key] = value
  }
  void router.replace({ query })
}

// The filters live in the URL, so results can be shared and the back button works.
watch(
  filters,
  (value) => {
    if (route.name !== 'properties') return
    void store.fetchList(value)
  },
  { immediate: true },
)

const summary = computed(() => {
  if (store.loading && !store.items.length) return 'Searching...'
  const n = store.count
  return `${n} ${n === 1 ? 'property' : 'properties'} found`
})
</script>

<template>
  <div class="pt-3 sm:pt-5">
    <section class="panel" aria-labelledby="properties-title">
      <div class="page-wrap py-8 lg:py-10">
        <h1 id="properties-title" class="text-3xl font-extrabold sm:text-4xl">Properties for rent</h1>
        <p class="mt-1 text-muted">Verified homes, reviewed by our team before they go live.</p>

        <div class="mt-6">
          <FilterBar :model-value="filters" @update:model-value="applyFilters" />
        </div>

        <p class="mt-6 font-semibold" role="status" aria-live="polite">{{ summary }}</p>

        <div v-if="store.error" class="mt-4 rounded-xl border border-brand p-4" role="alert">
          <p class="font-medium text-brand">{{ store.error }}</p>
          <button type="button" class="btn btn-outline mt-3" @click="store.fetchList(filters)">Try again</button>
        </div>

        <div v-else-if="!store.loading && !store.items.length" class="mt-4 rounded-xl border border-line p-6 text-center">
          <p class="text-lg font-semibold">No properties match your search.</p>
          <p class="mt-1 text-muted">Try a higher max price, fewer bedrooms, or a different city.</p>
          <button type="button" class="btn btn-primary mt-4" @click="applyFilters({})">Clear search and filters</button>
        </div>

        <TransitionGroup
          v-if="store.items.length"
          tag="ul"
          appear
          :css="false"
          class="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3"
          @before-enter="gridStagger.onBeforeEnter"
          @enter="gridStagger.onEnter"
          @before-appear="gridStagger.onBeforeEnter"
          @appear="gridStagger.onEnter"
        >
          <li v-for="(property, index) in store.items" :key="property.id" :data-index="index % 12">
            <PropertyCard :property="property" />
          </li>
        </TransitionGroup>

        <div v-if="store.hasMore" class="mt-8 text-center">
          <button type="button" class="btn btn-outline px-8" :disabled="store.loading" @click="store.loadMore(filters)">
            {{ store.loading ? 'Loading...' : 'Load more' }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
