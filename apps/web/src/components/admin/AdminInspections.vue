<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiFetch, parseApiError } from '@/lib/api'
import { formatDate } from '@/lib/datetime'
import { formatNaira } from '@/lib/money'
import type { Paged, StaffActionResult, StaffInspection } from '@/types'

type Decision = 'verify-payment' | 'confirm' | 'reject'

const emit = defineEmits<{ changed: [] }>()

const rows = ref<StaffInspection[]>([])
const count = ref(0)
const page = ref(1)
const statusFilter = ref('pending')
const paymentFilter = ref('all')
const search = ref('')
const loading = ref(false)
const busy = ref<number | null>(null)
const error = ref('')
const notice = ref('')

const pageSize = 20
const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize)))

function statusClass(value: string): string {
  if (value === 'confirmed') return 'bg-green-100 text-green-900'
  if (value === 'rejected') return 'bg-red-100 text-red-900'
  return 'bg-amber-100 text-amber-900'
}

function paymentClass(value: string): string {
  if (value === 'verified') return 'bg-green-100 text-green-900'
  if (value === 'not_required') return 'bg-slate-100 text-slate-800'
  return 'bg-amber-100 text-amber-900'
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const query: Record<string, string> = { page: String(page.value), page_size: String(pageSize) }
    if (statusFilter.value !== 'all') query.status = statusFilter.value
    if (paymentFilter.value !== 'all') query.payment_status = paymentFilter.value
    if (search.value.trim()) query.q = search.value.trim()
    const data = await apiFetch<Paged<StaffInspection>>('/staff/inspections', { query })
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

async function decide(item: StaffInspection, action: Decision): Promise<void> {
  busy.value = item.id
  error.value = ''
  notice.value = ''
  const done: Record<Decision, string> = {
    'verify-payment': 'Payment verified',
    confirm: 'Inspection confirmed',
    reject: 'Inspection rejected',
  }
  try {
    const result = await apiFetch<StaffInspection & StaffActionResult>(`/staff/inspections/${item.id}/${action}`, {
      method: 'POST',
    })
    notice.value = result.email_sent
      ? `${done[action]} for ${result.reference}. The visitor was emailed.`
      : `${done[action]} for ${result.reference}. ${result.email_error ?? 'No email was sent.'}`
    emit('changed')
    await load()
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    busy.value = null
  }
}

async function resend(item: StaffInspection): Promise<void> {
  busy.value = item.id
  error.value = ''
  notice.value = ''
  try {
    const result = await apiFetch<StaffInspection & StaffActionResult>(`/staff/inspections/${item.id}/resend-email`, {
      method: 'POST',
    })
    notice.value = result.email_sent
      ? `The latest email for ${result.reference} was sent to ${result.email}.`
      : `Could not resend the email for ${result.reference}. ${result.email_error ?? 'No email was sent.'}`
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
        <label for="inspection-status" class="label">Inspection</label>
        <select id="inspection-status" v-model="statusFilter" class="input w-auto" @change="applyFilters">
          <option value="pending">Pending</option>
          <option value="confirmed">Confirmed</option>
          <option value="rejected">Rejected</option>
          <option value="all">All</option>
        </select>
      </div>
      <div>
        <label for="inspection-payment" class="label">Payment</label>
        <select id="inspection-payment" v-model="paymentFilter" class="input w-auto" @change="applyFilters">
          <option value="all">All</option>
          <option value="unpaid">Unpaid</option>
          <option value="verified">Verified</option>
          <option value="not_required">No fee</option>
        </select>
      </div>
      <form class="flex flex-1 flex-wrap items-end gap-2" @submit.prevent="applyFilters">
        <div class="min-w-[220px] flex-1">
          <label for="inspection-search" class="label">Search</label>
          <input id="inspection-search" v-model="search" type="search" class="input" placeholder="Reference, name, phone or property" />
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
      <table class="w-full min-w-[980px] text-left text-sm">
        <caption class="sr-only">Inspection requests and their payment decisions</caption>
        <thead class="border-b border-line text-xs uppercase tracking-wide text-muted">
          <tr>
            <th scope="col" class="py-2 pr-4 font-semibold">Request</th>
            <th scope="col" class="py-2 pr-4 font-semibold">Property</th>
            <th scope="col" class="py-2 pr-4 font-semibold">Fee</th>
            <th scope="col" class="py-2 pr-4 font-semibold">Payment</th>
            <th scope="col" class="py-2 pr-4 font-semibold">Status</th>
            <th scope="col" class="py-2 font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id" class="border-b border-line align-top last:border-0">
            <td class="py-3 pr-4">
              <p class="font-semibold text-ink">{{ row.reference }} · {{ row.name }}</p>
              <p class="text-muted">{{ row.phone }} · {{ row.email }}</p>
              <p class="text-xs text-muted">{{ formatDate(row.preferred_date) }} · {{ formatDate(row.created_at) }}</p>
              <p v-if="row.note" class="mt-1 max-w-[260px] text-xs text-muted">“{{ row.note }}”</p>
            </td>
            <td class="py-3 pr-4">
              <p class="font-medium text-ink">{{ row.property_title }}</p>
              <p class="text-xs text-muted">{{ row.property_slug }}</p>
            </td>
            <td class="py-3 pr-4 whitespace-nowrap font-medium text-ink">
              {{ formatNaira(row.fee_amount) }}
              <p class="text-xs font-normal text-muted">{{ row.payment_choice_display }}</p>
            </td>
            <td class="py-3 pr-4">
              <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-bold" :class="paymentClass(row.payment_status)">
                {{ row.payment_status_display }}
              </span>
            </td>
            <td class="py-3 pr-4">
              <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-bold" :class="statusClass(row.status)">
                {{ row.status_display }}
              </span>
            </td>
            <td class="py-3">
              <div class="flex flex-wrap gap-2">
                <button
                  v-if="row.can_verify_payment"
                  type="button"
                  class="btn btn-primary min-h-9 px-3 py-1 text-sm"
                  :disabled="busy === row.id"
                  @click="decide(row, 'verify-payment')"
                >
                  Verify payment
                </button>
                <button
                  v-if="row.status === 'pending'"
                  type="button"
                  class="btn btn-outline min-h-9 px-3 py-1 text-sm"
                  :disabled="busy === row.id || !row.can_confirm"
                  :title="row.can_confirm ? 'Confirm this inspection' : 'Verify the payment first'"
                  @click="decide(row, 'confirm')"
                >
                  Confirm
                </button>
                <button
                  v-if="row.can_reject"
                  type="button"
                  class="btn btn-outline min-h-9 px-3 py-1 text-sm"
                  :disabled="busy === row.id"
                  @click="decide(row, 'reject')"
                >
                  Reject
                </button>
                <button
                  v-if="row.status !== 'pending' || row.payment_status === 'verified'"
                  type="button"
                  class="btn btn-outline min-h-9 px-3 py-1 text-sm"
                  :disabled="busy === row.id"
                  title="Send the latest decision email again without changing the inspection"
                  @click="resend(row)"
                >
                  Resend email
                </button>
              </div>
              <p v-if="row.status === 'pending' && !row.can_confirm" class="mt-1 text-xs font-medium text-brand">
                Verify the payment before confirming.
              </p>
            </td>
          </tr>
          <tr v-if="!rows.length && !loading">
            <td colspan="6" class="py-8 text-center text-muted">No inspections match this filter.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
      <p>{{ count }} inspection{{ count === 1 ? '' : 's' }}</p>
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
