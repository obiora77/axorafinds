<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiFetch, parseApiError } from '@/lib/api'
import { formatDate } from '@/lib/datetime'
import type { Paged, StaffActionResult, StaffReview } from '@/types'

const emit = defineEmits<{ changed: [] }>()

const rows = ref<StaffReview[]>([])
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

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const query: Record<string, string> = { page: String(page.value), page_size: String(pageSize) }
    if (statusFilter.value !== 'all') query.status = statusFilter.value
    if (search.value.trim()) query.q = search.value.trim()
    const data = await apiFetch<Paged<StaffReview>>('/staff/reviews', { query })
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

async function decide(review: StaffReview, action: 'publish' | 'unpublish'): Promise<void> {
  busy.value = review.id
  error.value = ''
  notice.value = ''
  try {
    const result = await apiFetch<StaffReview & StaffActionResult>(`/staff/reviews/${review.id}/${action}`, {
      method: 'POST',
    })
    if (action === 'publish') {
      notice.value = result.email_sent
        ? `${result.name}'s review is now on the home page. The author was emailed.`
        : `${result.name}'s review is now on the home page. ${result.email_note ?? result.email_error ?? 'No email was sent.'}`
    } else {
      notice.value = `${result.name}'s review was hidden from the home page.`
    }
    emit('changed')
    await load()
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    busy.value = null
  }
}

async function resend(review: StaffReview): Promise<void> {
  busy.value = review.id
  error.value = ''
  notice.value = ''
  try {
    const result = await apiFetch<StaffReview & StaffActionResult>(`/staff/reviews/${review.id}/resend-email`, {
      method: 'POST',
    })
    notice.value = result.email_sent
      ? `The published email for ${result.name}'s review was sent again.`
      : `Could not resend the email for ${result.name}'s review. ${result.email_error ?? 'No email was sent.'}`
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
        <label for="review-status" class="label">Status</label>
        <select id="review-status" v-model="statusFilter" class="input w-auto" @change="applyFilters">
          <option value="pending">Waiting for approval</option>
          <option value="published">Published</option>
          <option value="all">All reviews</option>
        </select>
      </div>
      <form class="flex flex-1 flex-wrap items-end gap-2" @submit.prevent="applyFilters">
        <div class="min-w-[220px] flex-1">
          <label for="review-search" class="label">Search</label>
          <input id="review-search" v-model="search" type="search" class="input" placeholder="Name, location or text" />
        </div>
        <button type="submit" class="btn btn-outline">Search</button>
      </form>
      <button type="button" class="btn btn-outline" :disabled="loading" @click="load">
        {{ loading ? 'Loading…' : 'Refresh' }}
      </button>
    </div>

    <p v-if="error" class="mt-4 rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ error }}</p>
    <p v-if="notice" class="mt-4 rounded-xl border border-line bg-white p-3 font-medium text-ink" role="status">{{ notice }}</p>

    <ul class="mt-4 space-y-3">
      <li v-for="row in rows" :key="row.id" class="rounded-2xl border border-line p-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p class="font-semibold text-ink">
              {{ row.name }}
              <span class="ml-2 text-amber-600" :aria-label="`${row.rating} out of 5 stars`">{{ '★'.repeat(row.rating) }}</span>
            </p>
            <p class="text-xs text-muted">
              {{ row.location || 'Location not given' }} · {{ formatDate(row.created_at) }}
              <span v-if="row.author_email"> · {{ row.author_email }}</span>
            </p>
          </div>
          <span
            class="inline-flex rounded-full px-2.5 py-1 text-xs font-bold"
            :class="row.is_published ? 'bg-green-100 text-green-900' : 'bg-amber-100 text-amber-900'"
          >
            {{ row.is_published ? 'Published' : 'Waiting' }}
          </span>
        </div>
        <p class="mt-3 text-ink">{{ row.text }}</p>
        <div class="mt-3 flex flex-wrap gap-2">
          <button
            v-if="!row.is_published"
            type="button"
            class="btn btn-primary min-h-9 px-3 py-1 text-sm"
            :disabled="busy === row.id"
            @click="decide(row, 'publish')"
          >
            {{ busy === row.id ? 'Publishing…' : 'Publish on home page' }}
          </button>
          <button
            v-else
            type="button"
            class="btn btn-outline min-h-9 px-3 py-1 text-sm"
            :disabled="busy === row.id"
            @click="decide(row, 'unpublish')"
          >
            Hide from home page
          </button>
          <button
            v-if="row.is_published && row.author_email"
            type="button"
            class="btn btn-outline min-h-9 px-3 py-1 text-sm"
            :disabled="busy === row.id"
            title="Send the published email again without changing the review"
            @click="resend(row)"
          >
            Resend email
          </button>
          <p v-if="!row.author_email && !row.is_published" class="self-center text-xs text-muted">
            No linked account — publishing will not email anyone.
          </p>
        </div>
      </li>
      <li v-if="!rows.length && !loading" class="rounded-2xl border border-line p-8 text-center text-muted">
        No reviews match this filter.
      </li>
    </ul>

    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
      <p>{{ count }} review{{ count === 1 ? '' : 's' }}</p>
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
