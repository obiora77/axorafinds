<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Heart, House, MapPin } from 'lucide-vue-next'
import { formatNaira } from '@/lib/money'
import { useAuthStore } from '@/stores/auth'
import { useFavoritesStore } from '@/stores/favorites'
import type { PropertyCardData } from '@/types'

const props = defineProps<{ property: PropertyCardData }>()

const auth = useAuthStore()
const favorites = useFavoritesStore()
const router = useRouter()
const imageFailed = ref(false)

const isFavorite = computed(() => favorites.has(props.property.id))
const heartDisabled = computed(() => auth.isAuthed && !auth.isSeeker)
const heartLabel = computed(() => {
  if (!auth.isAuthed) return 'Sign in to save this property'
  if (!auth.isSeeker) return 'Saving properties is available to seeker accounts'
  return isFavorite.value ? 'Remove from saved properties' : 'Save this property'
})

async function onHeart(): Promise<void> {
  if (!auth.isAuthed) {
    await router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  if (!auth.isSeeker) return
  try {
    await favorites.toggle(props.property.id)
  } catch {
    /* the store already rolled the heart back */
  }
}
</script>

<template>
  <article class="relative flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-white">
    <div class="relative">
      <img
        v-if="property.cover && !imageFailed"
        :src="property.cover"
        :alt="property.title"
        width="640"
        height="480"
        loading="lazy"
        decoding="async"
        class="aspect-4/3 w-full object-cover"
        @error="imageFailed = true"
      />
      <div v-else class="grid aspect-4/3 w-full place-items-center bg-line text-muted" role="img" :aria-label="property.title">
        <House class="size-10" aria-hidden="true" />
      </div>
      <span class="badge-rent absolute left-3 top-3">For Rent</span>
    </div>

    <div class="flex flex-1 flex-col gap-1 p-4">
      <p class="font-display text-xl font-extrabold text-black">{{ formatNaira(property.price) }}</p>
      <h3 class="text-base font-semibold text-ink">
        <RouterLink :to="`/properties/${property.slug}`" class="after:absolute after:inset-0 after:content-['']">
          {{ property.short_type }}<span class="sr-only">: {{ property.title }}</span>
        </RouterLink>
      </h3>
      <p class="flex items-center gap-1.5 text-sm text-muted">
        <MapPin class="size-4 shrink-0" aria-hidden="true" />
        {{ property.location }}
      </p>
    </div>

    <button
      type="button"
      class="absolute right-2 top-2 z-10 grid size-11 place-items-center rounded-full bg-white text-ink disabled:opacity-60"
      :aria-pressed="isFavorite"
      :aria-label="heartLabel"
      :title="heartLabel"
      :disabled="heartDisabled"
      @click.stop.prevent="onHeart"
    >
      <Heart class="size-5" :class="isFavorite ? 'text-brand' : ''" :fill="isFavorite ? 'currentColor' : 'none'" aria-hidden="true" />
    </button>
  </article>
</template>
