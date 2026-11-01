<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiFetch, parseApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/datetime'
import type { Paged, StaffContactMessage, StaffSubscriber } from '@/types'

const emit = defineEmits<{ changed: [] }>()

const messages = ref<StaffContactMessage[]>([])
const messageCount = ref(0)
const subscribers = ref<StaffSubscriber[]>([])
const subscriberCount = ref(0)
const search = ref('')
const loading = ref(false)
const deleting = ref<string | null>(null)
const error = ref('')
const notice = ref('')

async function loadMessages(): Promise<void> {
  const query: Record<string, string> = { page_size: '100' }
  if (search.value.trim()) query.q = search.value.trim()
  const data = await apiFetch<Paged<StaffContactMessage>>('/staff/messages', { query })
  messages.value = data.results
  messageCount.value = data.count
}

async function loadSubscribers(): Promise<void> {
  const data = await apiFetch<Paged<StaffSubscriber>>('/staff/subscribers', {
    query: { page_size: '100' },
  })
  subscribers.value = data.results
  subscriberCount.value = data.count
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadMessages(), loadSubscribers()])
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    loading.value = false
  }
}

async function removeMessage(item: StaffContactMessage): Promise<void> {
  if (!window.confirm(`Delete the message from ${item.name}? This cannot be undone.`)) return
  deleting.value = `message-${item.id}`
  error.value = ''
  notice.value = ''
  try {
    await apiFetch<unknown>(`/staff/messages/${item.id}`, { method: 'DELETE' })
    notice.value = 'Contact message deleted.'
    emit('changed')
    await loadMessages()
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    deleting.value = null
  }
}

async function removeSubscriber(item: StaffSubscriber): Promise<void> {
  if (!window.confirm(`Remove ${item.email} from the newsletter list?`)) return
  deleting.value = `subscriber-${item.id}`
  error.value = ''
  notice.value = ''
  try {
    await apiFetch<unknown>(`/staff/subscribers/${item.id}`, { method: 'DELETE' })
    notice.value = `${item.email} was removed from the newsletter list.`
    emit('changed')
    await loadSubscribers()
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    deleting.value = null
  }
}

onMounted(load)
</script>

<template>
  <div>
    <p v-if="error" class="rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ error }}</p>
    <p v-if="notice" class="mt-3 rounded-xl border border-line bg-white p-3 font-medium text-ink" role="status">{{ notice }}</p>

    <section class="mt-4" aria-labelledby="contact-messages">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="contact-messages" class="font-display text-xl font-bold text-ink">Contact messages</h2>
          <p class="text-sm text-muted">{{ messageCount }} in total. These are also stored in Django admin.</p>
        </div>
        <form class="flex items-end gap-2" @submit.prevent="load">
          <div>
            <label for="message-search" class="label">Search messages</label>
            <input id="message-search" v-model="search" type="search" class="input" placeholder="Name, email or text" />
          </div>
          <button type="submit" class="btn btn-outline" :disabled="loading">Search</button>
        </form>
      </div>

      <ul class="mt-4 space-y-3">
        <li v-for="item in messages" :key="item.id" class="rounded-2xl border border-line p-4">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p class="font-semibold text-ink">{{ item.name }}</p>
              <p class="text-xs text-muted">
                <a :href="`mailto:${item.email}`" class="text-brand hover:underline">{{ item.email }}</a>
                · {{ formatDateTime(item.created_at) }}
              </p>
            </div>
            <button
              type="button"
              class="btn btn-outline min-h-9 px-3 py-1 text-sm"
              :disabled="deleting === `message-${item.id}`"
              @click="removeMessage(item)"
            >
              Delete
            </button>
          </div>
          <p class="mt-3 whitespace-pre-line text-ink">{{ item.message }}</p>
        </li>
        <li v-if="!messages.length && !loading" class="rounded-2xl border border-line p-8 text-center text-muted">
          No contact messages yet.
        </li>
      </ul>
    </section>

    <section class="mt-8" aria-labelledby="newsletter-subscribers">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="newsletter-subscribers" class="font-display text-xl font-bold text-ink">Newsletter subscribers</h2>
          <p class="text-sm text-muted">{{ subscriberCount }} address{{ subscriberCount === 1 ? '' : 'es' }}.</p>
        </div>
        <button type="button" class="btn btn-outline" :disabled="loading" @click="loadSubscribers">
          {{ loading ? 'Loading…' : 'Refresh subscribers' }}
        </button>
      </div>

      <div class="mt-4 overflow-x-auto">
        <table class="w-full min-w-[520px] text-left text-sm">
          <caption class="sr-only">Newsletter subscribers</caption>
          <thead class="border-b border-line text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" class="py-2 pr-4 font-semibold">Email</th>
              <th scope="col" class="py-2 pr-4 font-semibold">Subscribed</th>
              <th scope="col" class="py-2 font-semibold">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in subscribers" :key="item.id" class="border-b border-line last:border-0">
              <td class="py-3 pr-4 font-medium text-ink">{{ item.email }}</td>
              <td class="py-3 pr-4 text-muted">{{ formatDateTime(item.created_at) }}</td>
              <td class="py-3">
                <button
                  type="button"
                  class="btn btn-outline min-h-9 px-3 py-1 text-sm"
                  :disabled="deleting === `subscriber-${item.id}`"
                  @click="removeSubscriber(item)"
                >
                  Remove
                </button>
              </td>
            </tr>
            <tr v-if="!subscribers.length && !loading">
              <td colspan="3" class="py-8 text-center text-muted">No subscribers yet.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
