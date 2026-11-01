<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { NG_STATES, PROPERTY_TYPES } from '@/lib/site'

const router = useRouter()
const q = ref('')
const selectedState = ref('')
const selectedType = ref('')

function submit(): void {
  const query: Record<string, string> = {}
  if (q.value.trim()) query.q = q.value.trim()
  if (selectedState.value) query.state = selectedState.value
  if (selectedType.value) query.type = selectedType.value
  void router.push({ name: 'properties', query })
}
</script>

<template>
  <form
    role="search"
    aria-label="Search verified properties"
    class="rounded-2xl border border-line bg-white p-3 sm:p-4"
    @submit.prevent="submit"
  >
    <div class="grid gap-3 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
      <div class="relative">
        <label for="home-search-q" class="sr-only">Search by area, street or keyword</label>
        <Search class="pointer-events-none absolute left-3.5 top-1/2 size-5 -translate-y-1/2 text-muted" aria-hidden="true" />
        <input id="home-search-q" v-model="q" type="search" placeholder="Area, street or keyword" class="input pl-11" />
      </div>
      <div>
        <label for="home-search-state" class="sr-only">State</label>
        <select id="home-search-state" v-model="selectedState" class="input">
          <option value="">Any state</option>
          <option v-for="item in NG_STATES" :key="item" :value="item">{{ item }}</option>
        </select>
      </div>
      <div>
        <label for="home-search-type" class="sr-only">Property type</label>
        <select id="home-search-type" v-model="selectedType" class="input">
          <option value="">Any type</option>
          <option v-for="item in PROPERTY_TYPES" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary md:px-8">Search homes</button>
    </div>
  </form>
</template>
