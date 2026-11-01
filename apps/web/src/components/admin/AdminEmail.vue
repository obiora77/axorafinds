<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { CircleCheck, MailWarning } from 'lucide-vue-next'
import { apiFetch, parseApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import type { EmailTestResult, StaffEmailStatus } from '@/types'

const emit = defineEmits<{ changed: [] }>()

const auth = useAuthStore()
const status = ref<StaffEmailStatus | null>(null)
const to = ref(auth.user?.email ?? '')
const loading = ref(true)
const sending = ref(false)
const error = ref('')
const notice = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    status.value = await apiFetch<StaffEmailStatus>('/staff/email')
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    loading.value = false
  }
}

async function sendTest(): Promise<void> {
  sending.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await apiFetch<EmailTestResult>('/staff/email/test', {
      method: 'POST',
      body: { to: to.value },
    })
    status.value = result.status
    if (result.sent) {
      notice.value = `A test message was accepted by the mail server for ${result.to}. Check that inbox and its Spam folder.`
    } else {
      error.value = result.error ?? 'The message was not sent. Check the configuration below.'
    }
    emit('changed')
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    sending.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="max-w-3xl">
    <h2 class="font-display text-xl font-bold text-ink">Email delivery</h2>
    <p class="mt-1 text-sm text-muted">
      Every form submission and staff decision uses these settings. A test message is sent through
      the exact backend and templates used by the site.
    </p>

    <p v-if="loading" class="mt-4 text-muted" role="status">Loading email status…</p>

    <template v-else>
      <p v-if="error" class="mt-4 rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ error }}</p>
      <p v-if="notice" class="mt-4 rounded-xl border border-line bg-white p-3 font-medium text-ink" role="status">{{ notice }}</p>

      <div
        v-if="status"
        class="mt-5 rounded-2xl border p-4"
        :class="status.enabled ? 'border-line' : 'border-brand'"
      >
        <div class="flex items-center gap-3">
          <CircleCheck v-if="status.enabled" class="size-5 text-green-700" aria-hidden="true" />
          <MailWarning v-else class="size-5 text-brand" aria-hidden="true" />
          <p class="font-semibold text-ink">
            {{ status.enabled ? 'The configured backend can send mail.' : 'Email is not configured yet.' }}
          </p>
        </div>
        <dl class="mt-4 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[180px_1fr]">
          <dt class="text-muted">Backend</dt>
          <dd class="break-all font-medium text-ink">{{ status.backend }}</dd>
          <dt class="text-muted">SMTP host / port</dt>
          <dd class="font-medium text-ink">{{ status.host ?? 'not set' }}<span v-if="status.port"> : {{ status.port }}</span></dd>
          <dt class="text-muted">Encryption</dt>
          <dd class="font-medium text-ink">{{ status.use_ssl ? 'SSL' : status.use_tls ? 'STARTTLS' : 'none' }}</dd>
          <dt class="text-muted">From address</dt>
          <dd class="break-all font-medium text-ink">{{ status.from_email }}</dd>
          <dt class="text-muted">Team address</dt>
          <dd class="break-all font-medium text-ink">{{ status.team_email }}</dd>
          <dt class="text-muted">Site URL in emails</dt>
          <dd class="break-all font-medium text-ink">{{ status.site_url }}</dd>
          <dt class="text-muted">Templates</dt>
          <dd class="font-medium" :class="status.templates_ready ? 'text-green-700' : 'text-brand'">
            {{ status.message_count }} messages ·
            {{ status.templates_ready ? 'all HTML and text parts found' : `${status.missing_templates.length} missing` }}
            <span v-if="status.missing_templates.length" class="block break-all text-xs">
              {{ status.missing_templates.join(', ') }}
            </span>
          </dd>
          <template v-if="status.last_error">
            <dt class="text-muted">Last error</dt>
            <dd class="break-words font-medium text-brand">{{ status.last_error }}</dd>
          </template>
        </dl>

        <p v-if="!status.enabled" class="mt-4 text-sm text-muted">
          Add <code>EMAIL_HOST</code>, <code>EMAIL_HOST_USER</code>, <code>EMAIL_HOST_PASSWORD</code>,
          <code>EMAIL_PORT</code> and <code>DEFAULT_FROM_EMAIL</code> to the repo-root <code>.env</code>,
          then restart the API. For Gmail use a 16-character App Password and
          <code>EMAIL_PORT=587</code>; if the connection is closed, try <code>EMAIL_PORT=465</code>
          with SSL instead.
        </p>
      </div>

      <form class="mt-6 rounded-2xl border border-line p-4" @submit.prevent="sendTest">
        <h3 class="font-display text-lg font-bold text-ink">Send a test email</h3>
        <label for="email-test-to" class="label mt-3">Send to</label>
        <div class="flex flex-wrap items-end gap-2">
          <input
            id="email-test-to"
            v-model="to"
            type="email"
            inputmode="email"
            autocomplete="email"
            class="input max-w-sm"
            required
          />
          <button type="submit" class="btn btn-primary" :disabled="sending || !to">
            {{ sending ? 'Sending…' : 'Send test email' }}
          </button>
        </div>
        <p class="hint">
          The result is shown here, including the exact SMTP error (for example a Gmail
          <code>535</code> authentication failure). Check the Spam folder before changing settings.
        </p>
      </form>
    </template>
  </div>
</template>
