<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight, CircleCheck, MailWarning } from 'lucide-vue-next'
import { formatDate } from '@/lib/datetime'
import { formatNaira } from '@/lib/money'
import type { StaffOverview } from '@/types'

type TabKey = 'listings' | 'inspections' | 'reviews' | 'messages' | 'settings' | 'email'

const props = defineProps<{ overview: StaffOverview | null; loading: boolean }>()
const emit = defineEmits<{ open: [tab: TabKey]; refresh: [] }>()

const tiles = computed(() => {
  const counts = props.overview?.counts
  if (!counts) return []
  return [
    {
      tab: 'listings' as TabKey,
      label: 'Listings to review',
      value: counts.listings.pending,
      hint: `${counts.listings.published} live`,
    },
    {
      tab: 'inspections' as TabKey,
      label: 'Inspections pending',
      value: counts.inspections.pending,
      hint: `${counts.inspections.ready_to_confirm} ready to confirm`,
    },
    {
      tab: 'inspections' as TabKey,
      label: 'Payments to verify',
      value: counts.inspections.awaiting_payment,
      hint: 'Bank-transfer and in-person fees',
    },
    {
      tab: 'reviews' as TabKey,
      label: 'Reviews to moderate',
      value: counts.reviews.pending,
      hint: `${counts.reviews.published} published`,
    },
    {
      tab: 'messages' as TabKey,
      label: 'Contact messages',
      value: counts.contacts,
      hint: 'Open the inbox',
    },
    {
      tab: 'messages' as TabKey,
      label: 'Newsletter subscribers',
      value: counts.subscribers,
      hint: `${counts.users.total} registered accounts`,
    },
  ]
})
</script>

<template>
  <div>
    <p v-if="loading && !overview" class="text-muted" role="status">Loading the queue…</p>

    <div v-else-if="!overview" class="rounded-2xl border border-line p-5">
      <p class="font-semibold text-ink">The overview could not be loaded.</p>
      <button type="button" class="btn btn-outline mt-3" @click="emit('refresh')">Try again</button>
    </div>

    <template v-else>
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <button
          v-for="tile in tiles"
          :key="tile.label"
          type="button"
          class="rounded-2xl border border-line p-4 text-left transition-colors hover:border-ink"
          @click="emit('open', tile.tab)"
        >
          <span class="text-3xl font-extrabold text-ink">{{ tile.value }}</span>
          <span class="mt-1 block font-semibold text-ink">{{ tile.label }}</span>
          <span class="text-sm text-muted">{{ tile.hint }}</span>
        </button>
      </div>

      <div class="mt-6 grid gap-5 lg:grid-cols-3">
        <section class="rounded-2xl border border-line p-4" aria-labelledby="recent-listings">
          <div class="flex items-center justify-between gap-2">
            <h2 id="recent-listings" class="font-display text-lg font-bold text-ink">New listings</h2>
            <button type="button" class="inline-flex items-center gap-1 text-sm font-semibold text-brand hover:underline" @click="emit('open', 'listings')">
              Open <ArrowRight class="size-4" aria-hidden="true" />
            </button>
          </div>
          <ul v-if="overview.recent.listings.length" class="mt-3 space-y-3">
            <li v-for="prop in overview.recent.listings" :key="prop.id" class="border-t border-line pt-3 first:border-0 first:pt-0">
              <p class="font-semibold text-ink">{{ prop.title }}</p>
              <p class="text-sm text-muted">{{ prop.location }} · {{ formatNaira(prop.price) }}</p>
              <p class="text-xs text-muted">{{ prop.owner_name }} · {{ formatDate(prop.created_at) }}</p>
            </li>
          </ul>
          <p v-else class="mt-3 text-sm text-muted">Nothing waiting to be reviewed.</p>
        </section>

        <section class="rounded-2xl border border-line p-4" aria-labelledby="recent-inspections">
          <div class="flex items-center justify-between gap-2">
            <h2 id="recent-inspections" class="font-display text-lg font-bold text-ink">Inspections pending</h2>
            <button type="button" class="inline-flex items-center gap-1 text-sm font-semibold text-brand hover:underline" @click="emit('open', 'inspections')">
              Open <ArrowRight class="size-4" aria-hidden="true" />
            </button>
          </div>
          <ul v-if="overview.recent.inspections.length" class="mt-3 space-y-3">
            <li v-for="item in overview.recent.inspections" :key="item.id" class="border-t border-line pt-3 first:border-0 first:pt-0">
              <p class="font-semibold text-ink">{{ item.reference }} · {{ item.name }}</p>
              <p class="text-sm text-muted">{{ item.property_title }}</p>
              <p class="text-xs text-muted">{{ item.preferred_date }} · {{ item.payment_status_display }}</p>
            </li>
          </ul>
          <p v-else class="mt-3 text-sm text-muted">No inspections are waiting.</p>
        </section>

        <section class="rounded-2xl border border-line p-4" aria-labelledby="recent-reviews">
          <div class="flex items-center justify-between gap-2">
            <h2 id="recent-reviews" class="font-display text-lg font-bold text-ink">Reviews to moderate</h2>
            <button type="button" class="inline-flex items-center gap-1 text-sm font-semibold text-brand hover:underline" @click="emit('open', 'reviews')">
              Open <ArrowRight class="size-4" aria-hidden="true" />
            </button>
          </div>
          <ul v-if="overview.recent.reviews.length" class="mt-3 space-y-3">
            <li v-for="review in overview.recent.reviews" :key="review.id" class="border-t border-line pt-3 first:border-0 first:pt-0">
              <p class="font-semibold text-ink">{{ review.name }} · {{ review.rating }}/5</p>
              <p class="line-clamp-2 text-sm text-muted">{{ review.text }}</p>
            </li>
          </ul>
          <p v-else class="mt-3 text-sm text-muted">No reviews are waiting.</p>
        </section>
      </div>

      <section class="mt-6 rounded-2xl border p-4" :class="overview.email.enabled ? 'border-line' : 'border-brand'" aria-labelledby="email-health">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-start gap-3">
            <CircleCheck v-if="overview.email.enabled" class="mt-0.5 size-5 text-green-700" aria-hidden="true" />
            <MailWarning v-else class="mt-0.5 size-5 text-brand" aria-hidden="true" />
            <div>
              <h2 id="email-health" class="font-display text-lg font-bold text-ink">Email delivery</h2>
              <p class="text-sm text-muted">
                {{ overview.email.enabled ? 'Configured' : 'Not configured' }} · {{ overview.email.backend }}
                <span v-if="overview.email.host"> · {{ overview.email.host }}</span>
              </p>
              <p v-if="overview.email.last_error" class="mt-1 text-sm font-medium text-brand">
                Last error: {{ overview.email.last_error }}
              </p>
              <p v-if="!overview.email.templates_ready" class="mt-1 text-sm font-medium text-brand">
                Missing templates: {{ overview.email.missing_templates.join(', ') }}
              </p>
            </div>
          </div>
          <button type="button" class="btn btn-outline" @click="emit('open', 'email')">Email settings</button>
        </div>
      </section>
    </template>
  </div>
</template>
