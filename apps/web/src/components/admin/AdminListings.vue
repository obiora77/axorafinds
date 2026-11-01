<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiFetch, parseApiError } from '@/lib/api'
import { formatDate } from '@/lib/datetime'
import { formatNaira } from '@/lib/money'
import type { ListingStatus, Paged, StaffActionResult, StaffListing } from '@/types'

const emit = defineEmits<{ changed: [] }>()

const rows = ref<StaffListing[]>([])
const count = ref(0)
const page = ref(1)
const statusFilter = ref('pending')
const search = ref('')
const loading = ref(false)
const busy = ref<number | null>(null)
const error = ref('')
const notice = ref('')

const pageSize = 20
const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize)))

function badgeClass(status: ListingStatus): string {
  if (status === 'published') return 'bg-green-100 text-green-900'
  if (status === 'rejected') return 'bg-red-100 text-red-900'
  return 'bg-amber-100 text-amber-900'
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const query: Record<string, string> = { page: String(page.value), page_size: String(pageSize) }
    if (statusFilter.value !== 'all') query.status = statusFilter.value
    if (search.value.trim()) query.q = search.value.trim()
    const data = await apiFetch<Paged<StaffListing>>('/staff/listings', { query })
    rows.value = data.results
    count.value = data.count
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    loading.value = false
  }
}

function applyFilters(): void {
  page.value = 1
  void load()
}

function go(next: number): void {
  if (next < 1 || next > totalPages.value) return
  page.value = next
  void load()
}

async function decide(listing: StaffListing, action: 'publish' | 'reject'): Promise<void> {
  busy.value = listing.id
  error.value = ''
  notice.value = ''
  const verb = action === 'publish' ? 'published' : 'rejected'
  try {
    const result = await apiFetch<StaffListing & StaffActionResult>(`/staff/listings/${listing.id}/${action}`, {
      method: 'POST',
    })
    notice.value = result.email_sent
      ? `${result.title} ${verb}. The owner was emailed.`
      : `${result.title} ${verb}. ${result.email_note ?? result.email_error ?? 'No email was sent.'}`
    emit('changed')
    await load()
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    busy.value = null
  }
}

async function resend(listing: StaffListing): Promise<void> {
  busy.value = listing.id
  error.value = ''
  notice.value = ''
  try {
    const result = await apiFetch<StaffListing & StaffActionResult>(`/staff/listings/${listing.id}/resend-email`, {
      method: 'POST',
    })
    notice.value = result.email_sent
      ? `The latest email for ${result.title} was sent to ${result.owner_email}.`
      : `Could not resend the email for ${result.title}. ${result.email_error ?? 'No email was sent.'}`
    emit('changed')
    await load()
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    busy.value = null
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="flex flex-wrap items-end gap-3">
      <div>
        <label for="listing-status" class="label">Status</label>
        <select id="listing-status" v-model="statusFilter" class="input w-auto" @change="applyFilters">
          <option value="pending">Pending review</option>
          <option value="published">Published</option>
          <option value="rejected">Rejected</option>
          <option value="all">All listings</option>
        </select>
      </div>
      <form class="flex flex-1 flex-wrap items-end gap-2" @submit.prevent="applyFilters">
        <div class="min-w-[220px] flex-1">
          <label for="listing-search" class="label">Search</label>
          <input id="listing-search" v-model="search" type="search" class="input" placeholder="Title, city or owner email" />
        </div>
        <button type="submit" class="btn btn-outline">Search</button>
      </form>
      <button type="button" class="btn btn-outline" :disabled="loading" @click="load">
        {{ loading ? 'Loading…' : 'Refresh' }}
      </button>
    </div>

    <p v-if="error" class="mt-4 rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ error }}</p>
    <p v-if="notice" class="mt-4 rounded-xl border border-line bg-white p-3 font-medium text-ink" role="status">{{ notice }}</p>

    <div class="mt-4 overflow-x-auto">
      <table class="w-full min-w-[860px] text-left text-sm">
        <caption class="sr-only">Listings waiting for staff review and published listings</caption>
        <thead class="border-b border-line text-xs uppercase tracking-wide text-muted">
          <tr>
            <th scope="col" class="py-2 pr-4 font-semibold">Listing</th>
            <th scope="col" class="py-2 pr-4 font-semibold">Rent</th>
            <th scope="col" class="py-2 pr-4 font-semibold">Photos</th>
            <th scope="col" class="py-2 pr-4 font-semibold">Status</th>
            <th scope="col" class="py-2 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-b border-line align-top last:border-0">
            <td class="py-3 pr-4">
              <p class="font-semibold text-ink">{{ row.title }}</p>
              <p class="text-muted">{{ row.location }} · {{ row.short_type }}</p>
              <p class="text-xs text-muted">{{ row.owner_name }} &lt;{{ row.owner_email }}&gt;</p>
              <p class="text-xs text-muted">Submitted {{ formatDate(row.created_at) }}</p>
            </td>
            <td class="py-3 pr-4 whitespace-nowrap font-medium text-ink">{{ formatNaira(row.price) }}</td>
            <td class="py-3 pr-4 text-muted">{{ row.photos_count }}</td>
            <td class="py-3 pr-4">
              <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-bold" :class="badgeClass(row.status)">
                {{ row.status }}
              </span>
            </td>
            <td class="py-3">
              <div class="flex flex-wrap gap-2">
                <button
                  v-if="row.status !== 'published'"
                  type="button"
                  class="btn btn-primary min-h-9 px-3 py-1 text-sm"
                  :disabled="busy === row.id || row.photos_count === 0"
                  @click="decide(row, 'publish')"
                >
                  {{ busy === row.id ? 'Working…' : 'Publish' }}
                </button>
                <button
                  v-if="row.status !== 'rejected'"
                  type="button"
                  class="btn btn-outline min-h-9 px-3 py-1 text-sm"
                  :disabled="busy === row.id"
                  @click="decide(row, 'reject')"
                >
                  Reject
                </button>
                <button
                  v-if="row.status !== 'pending'"
                  type="button"
                  class="btn btn-outline min-h-9 px-3 py-1 text-sm"
                  :disabled="busy === row.id"
                  title="Send the latest decision email again without changing the listing"
                  @click="resend(row)"
                >
                  Resend email
                </button>
              </div>
              <p v-if="row.photos_count === 0" class="mt-1 text-xs font-medium text-brand">
                Add a photo before publishing.
              </p>
            </td>
          </tr>
          <tr v-if="!rows.length && !loading">
            <td colspan="5" class="py-8 text-center text-muted">No listings match this filter.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
      <p>{{ count }} listing{{ count === 1 ? '' : 's' }}</p>
      <div class="flex items-center gap-2">
        <button type="button" class="btn btn-outline min-h-9 px-3 py-1 text-sm" :disabled="page <= 1 || loading" @click="go(page - 1)">
          Previous
        </button>
        <span>Page {{ page }} of {{ totalPages }}</span>
        <button type="button" class="btn btn-outline min-h-9 px-3 py-1 text-sm" :disabled="page >= totalPages || loading" @click="go(page + 1)">
          Next
        </button>
      </div>
    </div>
  </div>
</template>
