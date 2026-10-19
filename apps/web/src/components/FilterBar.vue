<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { Search, SlidersHorizontal, X } from 'lucide-vue-next'
import { BEDROOM_OPTIONS, NG_STATES, PROPERTY_TYPES } from '@/lib/site'
import type { PropertyFilters } from '@/types'

const props = defineProps<{ modelValue: PropertyFilters }>()
const emit = defineEmits<{ 'update:modelValue': [value: PropertyFilters] }>()

const draft = reactive<Required<PropertyFilters>>({
  q: '',
  state: '',
  city: '',
  type: '',
  max_price: '',
  bedrooms: '',
})
const open = ref(false)

watch(
  () => props.modelValue,
  (value) => {
    draft.q = value.q ?? ''
    draft.state = value.state ?? ''
    draft.city = value.city ?? ''
    draft.type = value.type ?? ''
    draft.max_price = value.max_price ?? ''
    draft.bedrooms = value.bedrooms ?? ''
  },
  { immediate: true, deep: true },
)

const activeCount = computed(
  () => [draft.state, draft.city, draft.type, draft.max_price, draft.bedrooms].filter(Boolean).length,
)
const anyActive = computed(() => activeCount.value > 0 || Boolean(draft.q))

function emitNow(): void {
  // Vue turns a type="number" input into a number, so normalise everything back to strings.
  const next: PropertyFilters = {}
  for (const [key, value] of Object.entries(draft)) {
    next[key as keyof PropertyFilters] = value === null || value === undefined ? '' : String(value)
  }
  emit('update:modelValue', next)
}
const emitSoon = useDebounceFn(emitNow, 400)

function clearAll(): void {
  Object.assign(draft, { q: '', state: '', city: '', type: '', max_price: '', bedrooms: '' })
  emitNow()
}
</script>

<template>
  <form role="search" aria-label="Search properties" class="space-y-3" @submit.prevent="emitNow">
    <div class="flex gap-2">
      <div class="relative min-w-0 flex-1">
        <label for="filter-q" class="sr-only">Search by area, street or keyword</label>
        <Search class="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-muted" aria-hidden="true" />
        <input
          id="filter-q"
          v-model="draft.q"
          type="search"
          placeholder="Search area, street or keyword"
          class="input pl-11"
          @input="emitSoon"
        />
      </div>
      <button
        type="button"
        class="btn btn-outline shrink-0 px-4 md:hidden"
        :aria-expanded="open"
        aria-controls="filter-fields"
        @click="open = !open"
      >
        <SlidersHorizontal class="size-5" aria-hidden="true" />
        Filters<span v-if="activeCount" class="ml-0.5 font-bold text-brand">({{ activeCount }})</span>
      </button>
    </div>

    <div
      id="filter-fields"
      class="grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5"
      :class="open ? 'grid' : 'hidden md:grid'"
    >
      <div>
        <label for="filter-state" class="label">State</label>
        <select id="filter-state" v-model="draft.state" class="input" @change="emitNow">
          <option value="">Any state</option>
          <option v-for="state in NG_STATES" :key="state" :value="state">{{ state }}</option>
        </select>
      </div>
      <div>
        <label for="filter-city" class="label">City</label>
        <input id="filter-city" v-model="draft.city" type="text" placeholder="e.g. Onitsha" class="input" @input="emitSoon" />
      </div>
      <div>
        <label for="filter-type" class="label">Type</label>
        <select id="filter-type" v-model="draft.type" class="input" @change="emitNow">
          <option value="">Any type</option>
          <option v-for="type in PROPERTY_TYPES" :key="type.value" :value="type.value">{{ type.label }}</option>
        </select>
      </div>
      <div>
        <label for="filter-price" class="label">Max price (NGN)</label>
        <input
          id="filter-price"
          v-model="draft.max_price"
          type="number"
          inputmode="numeric"
          min="0"
          step="10000"
          placeholder="e.g. 500000"
          class="input"
          @input="emitSoon"
        />
      </div>
      <div>
        <label for="filter-bedrooms" class="label">Bedrooms</label>
        <select id="filter-bedrooms" v-model="draft.bedrooms" class="input" @change="emitNow">
          <option v-for="option in BEDROOM_OPTIONS" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
      </div>
    </div>

    <button v-if="anyActive" type="button" class="inline-flex min-h-11 items-center gap-1.5 font-semibold text-brand hover:underline" @click="clearAll">
      <X class="size-4" aria-hidden="true" />
      Clear search and filters
    </button>
  </form>
</template>
