<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Bath, BedDouble, Check, ChevronLeft, ChevronRight, House, MapPin } from 'lucide-vue-next'
import InspectionForm from '@/components/InspectionForm.vue'
import { formatNaira, hasFee } from '@/lib/money'
import { prefersReducedMotion } from '@/plugins/motion'
import { usePropertiesStore } from '@/stores/properties'
import type { PropertyDetailData } from '@/types'

const route = useRoute()
const store = usePropertiesStore()

const property = ref<PropertyDetailData | null>(null)
const loading = ref(true)
const notFound = ref(false)
const error = ref('')
const active = ref(0)
const broken = ref<string[]>([])

const photos = computed(() => property.value?.photos ?? [])
const current = computed(() => photos.value[active.value])

onMounted(async () => {
  const slug = String(route.params.slug ?? '')
  try {
    property.value = await store.fetchOne(slug)
    document.title = `${property.value.short_type}, ${property.value.location} | Axora Finds`
  } catch (e) {
    const status = (e as { status?: number }).status
    if (status === 404) notFound.value = true
    else error.value = 'We could not load this property. Check your connection and try again.'
  } finally {
    loading.value = false
  }
})

function step(delta: number): void {
  const n = photos.value.length
  if (n) active.value = (active.value + delta + n) % n
}

function goToInspection(): void {
  const el = document.getElementById('inspection')
  if (!el) return
  const reduced = prefersReducedMotion()
  el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
  window.setTimeout(() => el.querySelector<HTMLElement>('input, button')?.focus({ preventScroll: true }), reduced ? 0 : 250)
}
</script>

<template>
  <div class="pt-3 sm:pt-5">
    <section class="panel" aria-labelledby="property-title">
      <div class="page-wrap py-6 lg:py-10">
        <RouterLink to="/properties" class="inline-flex min-h-11 items-center gap-2 font-semibold text-brand hover:underline">
          <ArrowLeft class="size-5" aria-hidden="true" />
          All properties
        </RouterLink>

        <p v-if="loading" class="mt-6 text-muted" role="status">Loading property...</p>

        <div v-else-if="notFound" class="mt-6">
          <h1 id="property-title" class="text-3xl font-extrabold">This property is not available</h1>
          <p class="mt-2 text-muted">It may have been rented out or taken down.</p>
          <RouterLink to="/properties" class="btn btn-primary mt-5">Browse properties</RouterLink>
        </div>

        <p v-else-if="error" class="mt-6 font-medium text-brand" role="alert">{{ error }}</p>

        <div v-else-if="property" class="mt-4 lg:grid lg:grid-cols-[minmax(0,1fr)_380px] lg:gap-10">
          <div>
            <div class="relative overflow-hidden rounded-2xl bg-line">
              <img
                v-if="current && !broken.includes(current.url)"
                :src="current.url"
                :alt="`${property.title}, photo ${active + 1} of ${photos.length}`"
                width="1200"
                height="800"
                class="aspect-4/3 w-full object-cover lg:aspect-16/10"
                @error="broken.push(current.url)"
              />
              <div v-else class="grid aspect-4/3 w-full place-items-center text-muted lg:aspect-16/10" role="img" :aria-label="property.title">
                <House class="size-14" aria-hidden="true" />
              </div>
              <span class="badge-rent absolute left-3 top-3">For Rent</span>
              <template v-if="photos.length > 1">
                <button type="button" class="absolute left-2 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full bg-white text-ink" aria-label="Previous photo" @click="step(-1)">
                  <ChevronLeft class="size-6" aria-hidden="true" />
                </button>
                <button type="button" class="absolute right-2 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full bg-white text-ink" aria-label="Next photo" @click="step(1)">
                  <ChevronRight class="size-6" aria-hidden="true" />
                </button>
              </template>
            </div>

            <ul v-if="photos.length > 1" class="mt-3 flex flex-wrap gap-2">
              <li v-for="(photo, index) in photos" :key="photo.id">
                <button
                  type="button"
                  class="block size-14 overflow-hidden rounded-lg border-2 sm:size-16"
                  :class="index === active ? 'border-ink' : 'border-transparent'"
                  :aria-label="`Show photo ${index + 1}`"
                  :aria-current="index === active"
                  @click="active = index"
                >
                  <img :src="photo.url" alt="" width="64" height="64" loading="lazy" class="size-full object-cover" />
                </button>
              </li>
            </ul>

            <div class="mt-6">
              <p class="font-display text-3xl font-extrabold text-black sm:text-4xl">{{ formatNaira(property.price) }}</p>
              <h1 id="property-title" class="mt-2 text-xl font-bold sm:text-2xl">{{ property.title }}</h1>
              <p class="mt-1 flex items-center gap-1.5 text-muted">
                <MapPin class="size-5 shrink-0" aria-hidden="true" />
                {{ property.location }}<template v-if="property.address">, {{ property.address }}</template>
              </p>

              <ul class="mt-4 flex flex-wrap gap-2">
                <li class="rounded-full border border-line px-3.5 py-1.5 font-semibold">{{ property.short_type }}</li>
                <li v-if="property.bedrooms" class="flex items-center gap-1.5 rounded-full border border-line px-3.5 py-1.5">
                  <BedDouble class="size-5" aria-hidden="true" />{{ property.bedrooms }} {{ property.bedrooms === 1 ? 'bedroom' : 'bedrooms' }}
                </li>
                <li v-if="property.bathrooms" class="flex items-center gap-1.5 rounded-full border border-line px-3.5 py-1.5">
                  <Bath class="size-5" aria-hidden="true" />{{ property.bathrooms }} {{ property.bathrooms === 1 ? 'bathroom' : 'bathrooms' }}
                </li>
              </ul>
            </div>

            <div class="mt-8">
              <h2 class="text-xl font-bold">About this property</h2>
              <p class="mt-2 max-w-prose whitespace-pre-line text-lg leading-relaxed">{{ property.description }}</p>
            </div>

            <div v-if="property.amenities.length" class="mt-8">
              <h2 class="text-xl font-bold">Amenities</h2>
              <ul class="mt-3 grid gap-2 sm:grid-cols-2">
                <li v-for="amenity in property.amenities" :key="amenity" class="flex items-center gap-2">
                  <Check class="size-5 shrink-0 text-brand" aria-hidden="true" />{{ amenity }}
                </li>
              </ul>
            </div>

            <div class="mt-8 rounded-2xl border border-line p-4">
              <h2 class="text-xl font-bold">Inspection</h2>
              <p v-if="hasFee(property.inspection_fee)" class="mt-1">
                Inspection fee: <strong class="text-black">{{ formatNaira(property.inspection_fee) }}</strong>. You choose to pay by bank transfer or in person when you request.
              </p>
              <p v-else class="mt-1">There is no inspection fee for this property.</p>
              <button type="button" class="btn btn-primary mt-4 w-full sm:w-auto" @click="goToInspection">Request inspection</button>
            </div>
          </div>

          <aside class="mt-8 lg:sticky lg:top-24 lg:mt-0 lg:self-start" aria-label="Request an inspection">
            <InspectionForm :key="property.id" :property="property" />
          </aside>
        </div>
      </div>
    </section>
  </div>
</template>
