<script setup lang="ts">
import { ref } from 'vue'
import { apiFetch, parseApiError } from '@/lib/api'

const email = ref('')
const status = ref<'idle' | 'busy' | 'done' | 'error'>('idle')
const message = ref('')

async function subscribe(): Promise<void> {
  const value = email.value.trim()
  if (!/^\S+@\S+\.\S+$/.test(value)) {
    status.value = 'error'
    message.value = 'Enter a valid email address.'
    return
  }
  status.value = 'busy'
  try {
    await apiFetch('/newsletter', { method: 'POST', body: { email: value }, auth: false })
    status.value = 'done'
    message.value = 'You are subscribed. Thank you.'
    email.value = ''
  } catch (e) {
    const parsed = parseApiError(e)
    status.value = 'error'
    message.value = parsed.fields.email || parsed.message
  }
}
</script>

<template>
  <form novalidate @submit.prevent="subscribe">
    <label for="newsletter-email" class="sr-only">Email address</label>
    <div class="flex gap-2">
      <input
        id="newsletter-email"
        v-model="email"
        type="email"
        inputmode="email"
        autocomplete="email"
        placeholder="Your email address"
        class="input min-w-0 flex-1"
        :aria-invalid="status === 'error'"
        aria-describedby="newsletter-status"
      />
      <button type="submit" class="btn btn-primary shrink-0 px-5" :disabled="status === 'busy'">
        {{ status === 'busy' ? 'Sending...' : 'Subscribe' }}
      </button>
    </div>
    <p
      id="newsletter-status"
      role="status"
      class="mt-2 min-h-5 text-sm"
      :class="status === 'error' ? 'font-semibold text-white underline decoration-brand decoration-2 underline-offset-4' : 'text-white'"
    >
      {{ message }}
    </p>
  </form>
</template>
