<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { Plus } from 'lucide-vue-next'
import PropertyCard from '@/components/PropertyCard.vue'
import { formatNaira } from '@/lib/money'
import { useAuthStore } from '@/stores/auth'
import { useFavoritesStore } from '@/stores/favorites'
import { usePropertiesStore } from '@/stores/properties'
import type { PropertyDetailData } from '@/types'

const auth = useAuthStore()
const favorites = useFavoritesStore()
const store = usePropertiesStore()

const firstName = computed(() => (auth.user?.name ?? '').trim().split(/\s+/)[0] || 'there')
const initials = computed(() => {
  const parts = (auth.user?.name ?? '').trim().split(/\s+/).filter(Boolean)
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? '').join('') || 'A'
})
const roleLabel = computed(() =>
  auth.isOwner ? 'Property owner' : auth.isSeeker ? 'Home seeker' : 'Staff account',
)

const savedPreview = computed(() => favorites.saved.slice(0, 3))
const ownerCounts = computed(() => ({
  published: store.mine.filter((property) => property.status === 'published').length,
  pending: store.mine.filter((property) => property.status === 'pending').length,
  rejected: store.mine.filter((property) => property.status === 'rejected').length,
}))
const recentListings = computed(() => store.mine.slice(0, 3))

const statusLabel: Record<PropertyDetailData['status'], string> = {
  published: 'Live',
  pending: 'In review',
  rejected: 'Rejected',
}
const statusClass: Record<PropertyDetailData['status'], string> = {
  published: 'bg-green-100 text-green-800',
  pending: 'bg-amber-100 text-amber-900',
  rejected: 'bg-red-100 text-red-800',
}

onMounted(() => {
  if (auth.isOwner) void store.fetchMine()
})
</script>

<template>
  <section aria-labelledby="member-title" class="rounded-3xl border border-line p-5 sm:p-6">
    <div class="flex flex-wrap items-start justify-between gap-5">
      <div class="flex items-center gap-4">
        <span class="grid size-14 shrink-0 place-items-center rounded-full bg-brand text-xl font-extrabold text-white" aria-hidden="true">
          {{ initials }}
        </span>
        <div>
          <p class="text-xs font-bold uppercase tracking-wide text-brand">{{ roleLabel }}</p>
          <h1 id="member-title" class="text-2xl font-extrabold sm:text-3xl">Welcome back, {{ firstName }}</h1>
          <p class="mt-1 text-sm text-muted">
            {{ auth.user?.email }}<template v-if="auth.user?.phone"> · {{ auth.user.phone }}</template>
          </p>
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <RouterLink to="/properties" class="btn btn-outline">Browse homes</RouterLink>
        <RouterLink v-if="auth.isOwner" to="/list-property" class="btn btn-primary">
          <Plus class="size-4" aria-hidden="true" />
          List a property
        </RouterLink>
      </div>
    </div>

    <div v-if="auth.isSeeker" class="mt-7 border-t border-line pt-6">
      <dl class="grid gap-3 sm:grid-cols-3">
        <div class="rounded-2xl border border-line p-4">
          <dt class="text-sm text-muted">Saved homes</dt>
          <dd class="text-2xl font-extrabold">{{ favorites.ids.size }}</dd>
        </div>
        <div class="rounded-2xl border border-line p-4">
          <dt class="text-sm text-muted">Verified listings</dt>
          <dd class="text-2xl font-extrabold">{{ store.latestLoading && !store.total ? '...' : store.total }}</dd>
        </div>
        <div class="rounded-2xl border border-line p-4">
          <dt class="text-sm text-muted">Account type</dt>
          <dd class="text-2xl font-extrabold">Seeker</dd>
        </div>
      </dl>

      <div class="mt-6 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 class="text-xl font-extrabold">Your saved homes</h2>
          <p class="text-sm text-muted">Tap the heart on any listing to keep it here.</p>
        </div>
        <RouterLink to="/properties" class="inline-flex min-h-11 items-center font-semibold text-brand hover:underline">
          Browse all homes
        </RouterLink>
      </div>

      <p v-if="favorites.savedLoading && !savedPreview.length" class="mt-3 text-muted" role="status">
        Loading your saved homes...
      </p>
      <ul v-else-if="savedPreview.length" class="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <li v-for="property in savedPreview" :key="property.id">
          <PropertyCard :property="property" />
        </li>
      </ul>
      <p v-else class="mt-3 rounded-2xl border border-dashed border-line p-4 text-muted">
        Nothing saved yet. Browse verified homes and tap the heart to come back to them later.
      </p>
    </div>

    <div v-else-if="auth.isOwner" class="mt-7 border-t border-line pt-6">
      <dl class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div class="rounded-2xl border border-line p-4">
          <dt class="text-sm text-muted">Live listings</dt>
          <dd class="text-2xl font-extrabold">{{ ownerCounts.published }}</dd>
        </div>
        <div class="rounded-2xl border border-line p-4">
          <dt class="text-sm text-muted">In review</dt>
          <dd class="text-2xl font-extrabold">{{ ownerCounts.pending }}</dd>
        </div>
        <div class="rounded-2xl border border-line p-4">
          <dt class="text-sm text-muted">Rejected</dt>
          <dd class="text-2xl font-extrabold">{{ ownerCounts.rejected }}</dd>
        </div>
        <div class="rounded-2xl border border-line p-4">
          <dt class="text-sm text-muted">Total listings</dt>
          <dd class="text-2xl font-extrabold">{{ store.mine.length }}</dd>
        </div>
      </dl>

      <div class="mt-6 flex flex-wrap items-end justify-between gap-2">
        <h2 class="text-xl font-extrabold">Your latest listings</h2>
        <RouterLink to="/list-property" class="inline-flex min-h-11 items-center font-semibold text-brand hover:underline">
          List another property
        </RouterLink>
      </div>

      <p v-if="store.mineLoading && !store.mine.length" class="mt-3 text-muted" role="status">Loading your listings...</p>
      <p v-else-if="store.mineError" class="mt-3 font-medium text-brand" role="alert">{{ store.mineError }}</p>
      <ul v-else-if="recentListings.length" class="mt-3 divide-y divide-line rounded-2xl border border-line">
        <li
          v-for="property in recentListings"
          :key="property.id"
          class="flex flex-wrap items-center justify-between gap-3 p-4"
        >
          <div class="min-w-0">
            <p class="truncate font-semibold">{{ property.title }}</p>
            <p class="text-sm text-muted">{{ property.location }} · {{ formatNaira(property.price) }}</p>
          </div>
          <div class="flex items-center gap-3">
            <span class="rounded-full px-3 py-1 text-xs font-bold" :class="statusClass[property.status]">
              {{ statusLabel[property.status] }}
            </span>
            <RouterLink
              v-if="property.status === 'published'"
              :to="`/properties/${property.slug}`"
              class="inline-flex min-h-11 items-center font-semibold text-brand hover:underline"
            >
              View
            </RouterLink>
          </div>
        </li>
      </ul>
      <p v-else class="mt-3 rounded-2xl border border-dashed border-line p-4 text-muted">
        You have not listed a property yet. Add photos and details, and our team will review it before it goes live.
      </p>
    </div>

    <div v-else class="mt-7 border-t border-line pt-6">
      <p class="font-semibold">Staff account</p>
      <p class="mt-1 text-muted">Verify inspection payments, confirm inspections and publish listings in the Django admin.</p>
    </div>
  </section>
</template>
