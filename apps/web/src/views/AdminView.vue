<script setup lang="ts">
import { onMounted, ref, type Component } from 'vue'
import {
  CalendarCheck2,
  Gauge,
  Inbox,
  ListChecks,
  MailWarning,
  MessageSquareQuote,
  Settings2,
} from 'lucide-vue-next'
import AdminEmail from '@/components/admin/AdminEmail.vue'
import AdminInspections from '@/components/admin/AdminInspections.vue'
import AdminListings from '@/components/admin/AdminListings.vue'
import AdminMessages from '@/components/admin/AdminMessages.vue'
import AdminOverview from '@/components/admin/AdminOverview.vue'
import AdminReviews from '@/components/admin/AdminReviews.vue'
import AdminSettings from '@/components/admin/AdminSettings.vue'
import { apiFetch, parseApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import type { StaffOverview } from '@/types'

type TabKey = 'overview' | 'listings' | 'inspections' | 'reviews' | 'messages' | 'settings' | 'email'

interface Tab {
  key: TabKey
  label: string
  icon: Component
}

const tabs: Tab[] = [
  { key: 'overview', label: 'Overview', icon: Gauge },
  { key: 'listings', label: 'Listings', icon: ListChecks },
  { key: 'inspections', label: 'Inspections', icon: CalendarCheck2 },
  { key: 'reviews', label: 'Reviews', icon: MessageSquareQuote },
  { key: 'messages', label: 'Messages', icon: Inbox },
  { key: 'settings', label: 'Settings', icon: Settings2 },
  { key: 'email', label: 'Email', icon: MailWarning },
]

const auth = useAuthStore()
const active = ref<TabKey>('overview')
const overview = ref<StaffOverview | null>(null)
const loading = ref(false)
const error = ref('')

async function loadOverview(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    overview.value = await apiFetch<StaffOverview>('/staff/overview')
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    loading.value = false
  }
}

function open(tab: TabKey): void {
  active.value = tab
}

onMounted(loadOverview)
</script>

<template>
  <section class="page-wrap py-6 sm:py-10" aria-labelledby="admin-title">
    <div class="flex flex-wrap items-end justify-between gap-4 text-white">
      <div>
        <p class="text-xs font-bold uppercase tracking-[0.22em] text-white/70">Staff tools</p>
        <h1 id="admin-title" class="mt-1 text-3xl font-extrabold sm:text-4xl">Operations dashboard</h1>
        <p class="mt-2 max-w-2xl text-white/85">
          Review listings, verify payments, confirm inspections and moderate reviews. Signed in as
          <strong class="font-semibold">{{ auth.user?.email }}</strong>.
        </p>
      </div>
      <RouterLink to="/" class="btn btn-light">View site</RouterLink>
    </div>

    <div class="mt-6 rounded-3xl bg-white p-4 sm:p-6">
      <div class="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Dashboard sections">
        <button
          v-for="tab in tabs"
          :id="`admin-tab-${tab.key}`"
          :key="tab.key"
          type="button"
          role="tab"
          :aria-selected="active === tab.key"
          :aria-controls="`admin-panel-${tab.key}`"
          :class="[
            'inline-flex min-h-11 shrink-0 items-center gap-2 rounded-full border px-4 text-sm font-semibold transition-colors',
            active === tab.key
              ? 'border-brand bg-brand text-white'
              : 'border-line bg-white text-ink hover:border-ink',
          ]"
          @click="active = tab.key"
        >
          <component :is="tab.icon" class="size-4" aria-hidden="true" />
          {{ tab.label }}
        </button>
      </div>

      <p v-if="error" class="mt-4 rounded-xl border border-brand p-3 font-medium text-brand" role="alert">
        {{ error }}
      </p>

      <div
        :id="`admin-panel-${active}`"
        class="mt-5"
        role="tabpanel"
        :aria-labelledby="`admin-tab-${active}`"
      >
        <AdminOverview
          v-if="active === 'overview'"
          :overview="overview"
          :loading="loading"
          @open="open"
          @refresh="loadOverview"
        />
        <AdminListings v-else-if="active === 'listings'" @changed="loadOverview" />
        <AdminInspections v-else-if="active === 'inspections'" @changed="loadOverview" />
        <AdminReviews v-else-if="active === 'reviews'" @changed="loadOverview" />
        <AdminMessages v-else-if="active === 'messages'" @changed="loadOverview" />
        <AdminSettings v-else-if="active === 'settings'" />
        <AdminEmail v-else-if="active === 'email'" @changed="loadOverview" />
      </div>
    </div>
  </section>
</template>
